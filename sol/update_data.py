# `python3 sol/update_data.py` automatically scrapes oracle's dataset csv files
from __future__ import annotations
import os
import re
import shutil
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from http.client import HTTPResponse
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlencode
from urllib.request import urlopen


FOLDER:str = "https://drive.google.com/drive/folders/1gLSw0RLjBbtaNy0dgnGQDAZOHIgCe-HH"
DOWNLOAD:str = "https://drive.usercontent.google.com/download"
DATA:Path = Path(__file__).resolve().parents[1] / "data"
MATCH_DATA:re.Pattern[str] = re.compile(r"\d{4}_LoL_esports_match_data_from_OraclesElixir\.csv")


class MatchFiles(HTMLParser):
  def __init__(self:MatchFiles)->None:
    super().__init__()
    self.files:dict[str, str] = {}
    self.file_id:str|None = None
    self.name:str|None = None
  def handle_starttag(self:MatchFiles, tag:str, attrs:list[tuple[str, str|None]])->None:
    if tag == "tr": self.file_id = dict(attrs).get("data-id")
    if tag == "strong" and self.file_id: self.name = ""
  def handle_data(self:MatchFiles, data:str)->None:
    if self.name is not None: self.name += data
  def handle_endtag(self:MatchFiles, tag:str)->None:
    if tag == "strong" and self.name is not None:
      if MATCH_DATA.fullmatch(self.name): self.files[self.name] = self.file_id # type: ignore
      self.name = None
    if tag == "tr": self.file_id = None


def require_file(response:HTTPResponse, name:str)->None:
  if response.headers.get_filename() == name: return
  if b"Quota exceeded" in response.read(4096):
    raise RuntimeError(f"Google Drive temporarily limited the public download of {name};\n\
this is most likely an issue with oracle's google drive, u can try downloading directly: {FOLDER}")
  raise RuntimeError(f"Google Drive did not return the CSV for {name}")

def update_data()->None:
  with urlopen(FOLDER, timeout=60) as response:
    page:str = response.read().decode("utf-8")
  parser = MatchFiles()
  parser.feed(page)
  if not parser.files: raise RuntimeError("No Oracle's Elixir match CSVs found in the download folder")
  DATA.mkdir(exist_ok=True)

  for name, file_id in sorted(parser.files.items(), reverse=True):
    url:str = f"{DOWNLOAD}?{urlencode({'id': file_id, 'export': 'download', 'confirm': 't'})}"
    with urlopen(url, timeout=60) as response:
      require_file(response, name)
      size:int = int(response.headers["Content-Length"])
      modified:int = int(parsedate_to_datetime(response.headers["Last-Modified"]).timestamp())
      path:Path = DATA / name
      if path.exists() and path.stat().st_size == size and int(path.stat().st_mtime) == modified:
        print(f"Up to date: {path}", flush=True)
        continue

      temporary:Path|None = None
      try:
        with NamedTemporaryFile(dir=DATA, prefix=f".{name}.", delete=False) as temp:
          temporary = Path(temp.name)
          shutil.copyfileobj(response, temp)
        if temporary.stat().st_size != size: raise RuntimeError(f"Incomplete download: {name}")
        temporary.replace(path)
      finally:
        if temporary: temporary.unlink(missing_ok=True)
      os.utime(path, (modified, modified))
      print(f"Downloaded: {path}", flush=True)


if __name__ == "__main__": update_data()

# [Leakage and the Reproducibility Crisis in ML-based Science](https://arxiv.org/pdf/2207.07048)
TLDR:
- **do not** pre-process, impute, feature selection, etc... **ON TEST SET** (L1.2, L1.3, L1.4)
- test set **should** only have the most recent data (max(training date) < min(test date)) L3.1

```
[L1.2] Pre-processing on training and test set. Using the entire dataset for any pre-processing steps such as imputation
or over/under sampling. For instance, using oversampling
before splitting the data into training and test sets leads to
an imperfect separation between the training and test sets
since data generated using oversampling from the training
set will also be present in the test set.
[L1.3] Feature selection on training and test set. Feature
selection on the entire dataset results in using information
about which feature performs well on the test set to make
a decision about which features should be included in the
model.
[L1.4] Duplicates in datasets. If a dataset with duplicates
is used for the purposes of training and evaluating an ML
model, the same data could exist in the training as well as
test set.

[L3.1] Temporal leakage. When an ML model is used to
make predictions about a future outcome of interest, the
test set should not contain any data from a date before the
training set. If the test set contains data from before the
training set, the model is built using data “from the future”
that it should not have access to during training, and can
cause leakage.
```

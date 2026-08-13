# [Leakage and the Reproducibility Crisis in ML-based Science](https://arxiv.org/pdf/2207.07048)
- **do not** pre-process, impute, feature selection, etc... **ON TEST SET** (L1.2, L1.3, L1.4)
- test set **should** only have the most recent data (max(training date) < min(test date)); This results in better future performance evaluation L3.1
- entries in both test and train data should be independent. L3.2 llm example:
``` 
bad: temporal and dependence leakage
Train: Games 1, 2 and 4
Test:  Game 3
```
- do not select or eliminate any traintest data because it will introduce bias, L3.3
```
bad: worlds bias
Train: 2022–2024 worldwide professional matches
Test:  late 2025, but only Worlds matches
```

highlights:
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
[L3.2] Nonindependence between train and test samples.
Nonindependence between train and test samples constitutes
leakage, unless the scientific claim is about a distribution
that has the same dependence structure. In the extreme (but
unfortunately common) case, train and test samples come
from the same people or units. For example, Oner et al.
(2020) find that a recent study on histopathology uses different
observations of the same patient in the training and test
sets. In this case, the scientific claim is being made about
the ability to predict gene mutations in new patients;
however, it is evaluated on data from old patients (i.e., data from
patients in the training set), leading to a mismatch between
the test set distribution and the scientific claim.
The traintest split should account for the dependencies in the data
[L3.3] Sampling bias in test distribution. Sampling bias
in the choice of test dataset can lead to data leakage. One
example of sampling bias is spatial bias, which refers to
choosing the test data from a geographic location but making claims about model performance in other geographic
locations as well. Another example is selection bias, which
entails choosing a non-representative subset of the dataset
for evaluation. For example, Bone et al. (2015) highlight
that in a study on predicting autism using ML models, excluding the data corresponding to borderline cases of autism
leads to leakage since the test set is no longer representative
of the general population about which claims are made
```

# [DraftRec: Personalized Draft Recommendation for Winning in Multi-Player Online Battle Arena Games](https://arxiv.org/pdf/2207.07048)
- found some parts of the underlying architecture to be quite faulty/badly thought, but overall goal is still achieved
- they do multi models like sol will do: 1 for player preference and 1 for match outcome prediction
- use of sin waves for "temporal" context which is interesting
- they use UNK/Undefined for the draft engine
- **how picks are stored:**


The entire drafting process illustrated in Section 3.1 can be formalized as follows. 
Let us denote a single match as $m^i$ (for $1 \leq i \leq M$, where $M$ is the total number of matches in our training data) which is composed of 10 champion selections, one per each player. 
Players $[p_1^i, \cdots, p_{10}^i]$ (where $p_t^i$ represents the player at turn $t$ in match $m^i$) are evenly divided into two teams, Blue $[p_t^i]{t=1,4,5,8,9}$ and Purple $[p_t^i]{t=2,3,6,7,10}$ as shown in Fig. 1(b). Here, the ground-truth champion, role, match outcome (e.g., win or lose) and team of $p_t^i$ are respectively defined as $c_t^i$, $r_t^i$, $o_t^i$ and $team_t^i$.
<img width="1590" height="628" alt="image" src="https://github.com/user-attachments/assets/d97099ad-745f-46eb-ae69-df3c092e3aee" />

# Learning representations by back-propagating errors
# Pranking with Ranking
# Learning to Rank using Gradient Descent

## Stratified classification for multi-modal TCGA data

This directory stores scripts to run classification experiments and analyze/plot the results.
We use various data modalities to predict cancer type and gene alteration status in TCGA, with train and test sets that are stratified by cancer type (i.e. that have approximately equal proportions of each cancer type and subtype catalogued in TCGA).

The goal is to compare the utility of different data modalities for each cancer type and each gene alteration.
For details on how the mutation data and cancer type data is preprocessed and filtered, see [the notes in the BioBombe repo](https://github.com/greenelab/BioBombe/tree/master/9.tcga-classify).
Here, we use the same mutation and copy number data, as well as the same preprocessing steps to generate cancer type labels.

### Predicting cancer types

TCGA has profiled 33 different cancer types.
We trained classifiers to distinguish each cancer type from all others ("one-vs-rest" classification), using each data modality separately.

### Predicting mutations

We trained classifiers to predict mutation status in a set of cancer genes derived from [Vogelstein and Kinzler 2004](https://www.nature.com/articles/nm1087). We also use each data modality separately for now.

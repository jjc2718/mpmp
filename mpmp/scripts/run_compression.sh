#!/bin/bash
RESULTS_DIR=./compressed_results
ERRORS_DIR=./compressed_results_errors

mkdir -p $ERRORS_DIR

for n_dim in 100 500 1000; do
    for data_type in me_450k me_27k expression; do
        cmd="python 02_classify_compressed/run_mutation_compressed.py --gene_set vogelstein --results_dir $RESULTS_DIR --n_dim ${n_dim} --training_data ${data_type} 2>$ERRORS_DIR/compressed_results_errors_${data_type}_${n_dim}.txt"
        echo "Running: $cmd"
        eval $cmd
    done
done

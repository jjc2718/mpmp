"""
Script to run one-vs-rest cancer type classification, with stratified train and
test sets, for all provided TCGA cancer types.
"""
import sys
import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

import mpmp.config as cfg
from mpmp.data_models.tcga_data_model import TCGADataModel
from mpmp.exceptions import (
    ResultsFileExistsError,
    NoTrainSamplesError,
    NoTestSamplesError,
    OneClassError,
)
from mpmp.utilities.classify_utilities import run_cv_stratified
import mpmp.utilities.data_utilities as du
import mpmp.utilities.file_utilities as fu
from mpmp.utilities.tcga_utilities import get_overlap_data_types

def process_args():
    """Parse and format command line arguments."""

    parser = argparse.ArgumentParser()

    # argument group for parameters related to input/output
    # (e.g. filenames, logging/verbosity options, target genes)
    #
    # these don't affect the model output, and thus don't need to be saved
    # with the results of the experiment
    io = parser.add_argument_group('io',
                                   'arguments related to script input/output, '
                                   'note these will *not* be saved in metadata ')
    io.add_argument('--cancer_types', nargs='*',
                    help='cancer types to predict, if not included predict '
                        'all cancer types in TCGA')
    io.add_argument('--log_file', default=None,
                    help='name of file to log skipped cancer types to')
    io.add_argument('--output_preds', action='store_true')
    io.add_argument('--results_dir', default=cfg.results_dir,
                    help='where to write results to')
    io.add_argument('--verbose', action='store_true')

    # argument group for parameters related to model training/evaluation
    # (e.g. model hyperparameters, preprocessing options)
    #
    # these affect the output of the model, so we want to save them in the
    # same directory as the experiment results
    opts = parser.add_argument_group('model_options',
                                     'parameters for training/evaluating model, '
                                     'these will affect output and are saved as '
                                     'experiment metadata ')
    opts.add_argument('--debug', action='store_true',
                      help='use subset of data for fast debugging')
    opts.add_argument('--num_folds', type=int, default=4,
                      help='number of folds of cross-validation to run')
    opts.add_argument('--seed', type=int, default=cfg.default_seed)
    opts.add_argument('--subset_mad_genes', type=int, default=cfg.num_features_raw,
                      help='if included, subset gene features to this number of '
                           'features having highest mean absolute deviation')
    opts.add_argument('--training_data', type=str, default='expression',
                      choices=list(cfg.data_types.keys()),
                      help='what data type to train model on')

    args = parser.parse_args()

    args.results_dir = Path(args.results_dir).resolve()

    if args.log_file is None:
        args.log_file = Path(args.results_dir, 'log_skipped.tsv').resolve()

    # check that all provided cancer types are valid TCGA acronyms
    sample_info_df = du.load_sample_info(args.training_data, args.verbose)
    tcga_cancer_types = list(np.unique(sample_info_df.cancer_type))

    if args.cancer_types is None:
        args.cancer_types = tcga_cancer_types
    else:
        not_in_tcga = set(args.cancer_types) - set(tcga_cancer_types)
        if len(not_in_tcga) > 0:
            parser.error('some cancer types not present in TCGA: {}'.format(
                         ' '.join(not_in_tcga)))

    # split args into defined argument groups, since we'll use them differently
    arg_groups = du.split_argument_groups(args, parser)
    io_args, model_options = arg_groups['io'], arg_groups['model_options']

    # add some additional hyperparameters/ranges from config file to model options
    # these shouldn't be changed by the user, so they aren't added as arguments
    model_options.alphas = cfg.alphas
    model_options.l1_ratios = cfg.l1_ratios
    model_options.standardize_data_types = cfg.standardize_data_types

    # add information about valid samples to model options
    model_options.sample_overlap_data_types = list(
        get_overlap_data_types(debug=model_options.debug).keys()
    )

    return io_args, model_options, sample_info_df


if __name__ == '__main__':

    # process command line arguments
    io_args, model_options, sample_info_df = process_args()

    # create results dir and subdir for experiment if they don't exist
    experiment_dir = Path(io_args.results_dir, 'cancer_type').resolve()
    experiment_dir.mkdir(parents=True, exist_ok=True)

    # save model options for this experiment
    # (hyperparameters, preprocessing info, etc)
    fu.save_model_options(experiment_dir, model_options)

    # create empty error log file if it doesn't exist
    log_columns = [
        'cancer_type',
        'training_data',
        'shuffle_labels',
        'skip_reason'
    ]
    if io_args.log_file.exists() and io_args.log_file.is_file():
        log_df = pd.read_csv(io_args.log_file, sep='\t')
    else:
        log_df = pd.DataFrame(columns=log_columns)
        log_df.to_csv(io_args.log_file, sep='\t')

    # load data matrix for the specified data type
    tcga_data = TCGADataModel(seed=model_options.seed,
                              subset_mad_genes=model_options.subset_mad_genes,
                              training_data=model_options.training_data,
                              sample_info_df=sample_info_df,
                              verbose=io_args.verbose,
                              debug=model_options.debug)

    # we want to run cancer type classification experiments:
    # - for true labels and shuffled labels
    #   (shuffled labels acts as our lower baseline)
    # - for all cancer types in the given list of TCGA cancers
    for shuffle_labels in (False, True):

        print('shuffle_labels: {}'.format(shuffle_labels))

        progress = tqdm(io_args.cancer_types,
                        total=len(io_args.cancer_types),
                        ncols=100,
                        file=sys.stdout)

        for cancer_type in progress:
            cancer_type_log_df = None
            progress.set_description('cancer type: {}'.format(cancer_type))

            try:
                cancer_type_dir = fu.make_output_dir(experiment_dir, cancer_type)
                check_file = fu.check_output_file(cancer_type_dir,
                                                  cancer_type,
                                                  shuffle_labels,
                                                  model_options)
                tcga_data.process_data_for_cancer_type(cancer_type,
                                                       cancer_type_dir,
                                                       shuffle_labels=shuffle_labels)
            except ResultsFileExistsError:
                # this happens if cross-validation for this cancer type has
                # already been run (i.e. the results file already exists)
                if io_args.verbose:
                    print('Skipping because results file exists already: '
                          'cancer type {}'.format(cancer_type), file=sys.stderr)
                cancer_type_log_df = fu.generate_log_df(
                    log_columns,
                    [cancer_type, model_options.training_data, shuffle_labels, 'file_exists']
                )
                fu.write_log_file(cancer_type_log_df, io_args.log_file)
                continue

            try:
                # for now, don't standardize methylation data
                standardize_columns = (model_options.training_data in
                                       cfg.standardize_data_types)
                results = run_cv_stratified(tcga_data,
                                            'cancer_type',
                                            cancer_type,
                                            model_options.training_data,
                                            sample_info_df,
                                            model_options.num_folds,
                                            shuffle_labels,
                                            standardize_columns,
                                            io_args.output_preds)
                # only save results if no exceptions
                fu.save_results(cancer_type_dir,
                                check_file,
                                results,
                                'cancer_type',
                                cancer_type,
                                shuffle_labels,
                                model_options)
            except NoTestSamplesError:
                if io_args.verbose:
                    print('Skipping due to no test samples: cancer type '
                          '{}'.format(cancer_type), file=sys.stderr)
                cancer_type_log_df = fu.generate_log_df(
                    log_columns,
                    [cancer_type, model_options.training_data, shuffle_labels, 'no_test_samples']
                )
            except OneClassError:
                if io_args.verbose:
                    print('Skipping due to one holdout class: cancer type '
                          '{}'.format(cancer_type), file=sys.stderr)
                cancer_type_log_df = fu.generate_log_df(
                    log_columns,
                    [cancer_type, model_options.training_data, shuffle_labels, 'one_class']
                )

            if cancer_type_log_df is not None:
                fu.write_log_file(cancer_type_log_df, io_args.log_file)


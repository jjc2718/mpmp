"""
Functions for writing and processing output files
"""
from pathlib import Path
import pickle as pkl

import pandas as pd

from mpmp.exceptions import ResultsFileExistsError

def make_output_dir(experiment_dir, identifier):
    """Create a directory to write output to."""
    output_dir = Path(experiment_dir, identifier).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def construct_filename(output_dir,
                       file_descriptor,
                       extension,
                       *args,
                       **kwargs):
    """Construct a filename from varying experimental parameters.

    The format of the filename will roughly look like this:
    {output_dir}/{a}_{k}_{file_descriptor}{extension}
    where a = '_'.join([ar for ar in args]),
          k = '_'.join(['{k}{v} for k, v in kwargs.items()])

    For example:
    >>> construct_filename('output_dir', 'output', '.tsv',
    ...                    'expression', 'signal',
    ...                    s=42, n=5000)
    output_dir/expression_signal_s42_n5000_output.tsv

    Also note that if a parameter has a value of None, it will be silently
    skipped in the output filename.
    """
    if len(args) == 0 and len(kwargs) == 0:
        return Path(output_dir,
                    '{}{}'.format(file_descriptor, extension))
    elif len(args) == 0:
        return Path(output_dir,
                    '{}_{}{}'.format('_'.join([f'{k}{v}' for k, v in kwargs.items()
                                                             if v is not None]),
                                     file_descriptor,
                                     extension))
    elif len(kwargs) == 0:
        return Path(output_dir,
                    '{}_{}{}'.format('_'.join([ar for ar in args if ar is not None]),
                                     file_descriptor,
                                     extension))
    else:
        return Path(output_dir,
                    '{}_{}_{}{}'.format('_'.join([ar for ar in args if ar is not None]),
                                        '_'.join([f'{k}{v}' for k, v in kwargs.items()
                                                                if v is not None]),
                                        file_descriptor,
                                        extension))


def save_model_options(output_dir, model_options):
    """Save model hyperparameters/metadata to output directory.

    model_options is an argparse Namespace, and is converted to a dictionary
    and pickled.
    """
    output_file = construct_filename(output_dir,
                                     'model_options',
                                     '.pkl',
                                     model_options.training_data,
                                     s=model_options.seed)
    with open(output_file, 'wb') as f:
        pkl.dump(vars(model_options), f)


def check_output_file(output_dir,
                      identifier,
                      shuffle_labels,
                      model_options):
    """Check if results already exist for a given experiment identifier.

    If the file does not exist, return the filename.
    """

    signal = 'shuffled' if shuffle_labels else 'signal'
    check_file = construct_filename(output_dir,
                                    'coefficients',
                                    '.tsv.gz',
                                    identifier,
                                    model_options.training_data,
                                    signal,
                                    s=model_options.seed,
                                    n=model_options.n_dim)
    if check_file.is_file():
        raise ResultsFileExistsError(
            'Results file already exists for identifier: {}\n'.format(
                identifier)
        )
    return check_file


def save_results(output_dir,
                 check_file,
                 results,
                 exp_string,
                 identifier,
                 shuffle_labels,
                 model_options):
    """Save results of a single experiment for a single identifier."""

    auc_df = pd.concat(results[
        '{}_auc'.format(exp_string)
    ])
    aupr_df = pd.concat(results[
        '{}_aupr'.format(exp_string)
    ])
    coef_df = pd.concat(results[
        '{}_coef'.format(exp_string)
    ])
    metrics_df = pd.concat(results[
        '{}_metrics'.format(exp_string)
    ])

    if '{}_preds'.format(exp_string) in results:
        preds_df = pd.concat(results[
            '{}_preds'.format(exp_string)
        ])
    else:
        preds_df = None

    coef_df.to_csv(
        check_file, sep="\t", index=False, float_format="%.5g"
    )

    signal = 'shuffled' if shuffle_labels else 'signal'

    output_file = construct_filename(output_dir,
                                     'auc_threshold_metrics',
                                     '.tsv.gz',
                                     identifier,
                                     model_options.training_data,
                                     signal,
                                     s=model_options.seed,
                                     n=model_options.n_dim)
    auc_df.to_csv(
        output_file, sep="\t", index=False, float_format="%.5g"
    )

    output_file = construct_filename(output_dir,
                                     'aupr_threshold_metrics',
                                     '.tsv.gz',
                                     identifier,
                                     model_options.training_data,
                                     signal,
                                     s=model_options.seed,
                                     n=model_options.n_dim)
    aupr_df.to_csv(
        output_file, sep="\t", index=False, float_format="%.5g"
    )

    output_file = construct_filename(output_dir,
                                     'classify_metrics',
                                     '.tsv.gz',
                                     identifier,
                                     model_options.training_data,
                                     signal,
                                     s=model_options.seed,
                                     n=model_options.n_dim)
    metrics_df.to_csv(
        output_file, sep="\t", index=False, float_format="%.5g"
    )

    if preds_df is not None:
        output_file = construct_filename(output_dir,
                                         'preds',
                                         '.tsv.gz',
                                         identifier,
                                         model_options.training_data,
                                         signal,
                                         s=model_options.seed,
                                         n=model_options.n_dim)
        preds_df.to_csv(
            output_file, sep="\t", float_format="%.5g"
        )


def generate_log_df(log_columns, log_values):
    """Generate and format log output."""
    return pd.DataFrame(dict(zip(log_columns, log_values)), index=[0])


def write_log_file(log_df, log_file):
    """Append log output to log file."""
    log_df.to_csv(log_file, mode='a', sep='\t', index=False, header=False)


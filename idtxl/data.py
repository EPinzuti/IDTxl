"""Provide data structures for IDTxl analysis.

Created on Mon Mar  7 18:13:27 2016

@author: patricia
"""
import copy as cp
import numpy as np
from . import idtxl_utils as utils

VERBOSE = True


class Data():
    """Store data for information dynamics estimation.

    Data takes a 1- to 3-dimensional array representing realisations of random
    variables in dimensions: processes, samples (over time), and replications.
    If necessary, data reshapes provided realisations to fit the format
    expected by IDTxl, which is a 3-dimensional array with axes representing
    (process index, sample index, replication index). Indicate the actual order
    of dimensions in the provided array in a three-character string, e.g. 'spr'
    for an array with realisations over (1) samples in time, (2) processes, (3)
    replications.

    Examples:
        d_mute = Data()              # initialise empty data object
        d_mute.generate_mute_data()  # simulate data from MuTE paper
        dat = np.arange(10000).reshape((2, 1000, 5))  # random data: 2 procs.,
        d1 = Data(dat, dim_order='psr')               # 1000 samples, 5 repl.
        dat = np.arange(3000).reshape((3, 1000))  # random data: 3 procs.,
        d2 = Data(dat, dim_order='ps')            # 1000 samples
        dat_new = np.arange(5000)
        d2.set_data(dat_new, 's')  # set new data for the existing object

    Note:
        Realisations are stored as attribute 'data'. This can't be set
        directly, but only via the method 'set_data'

    Args:
        data : numpy array [optional]
            1/2/3-dimensional array with raw data
        dim_order : string [optional]
            order of dimensions, accepts any combination of the characters
            'p', 's', and 'r' for processes, samples, and replications; must
            have the same length as the data dimensionality, e.g., 'ps' for a
            two-dimensional array of data from several processes over time
            (default='psr')
        normalise : bool [optional]
            if True, data gets normalised per process (default=True)

    Attributes:
        data : numpy array
            realisations, can only be set via 'set_data' method
        n_processes : int
            number of processes
        n_replications : int
            number of replications
        n_samples : int
            number of samples in time
        normalise : bool
            if true, all data gets z-standardised per process

    """

    def __init__(self, data=None, dim_order='psr', normalise=True):
        self.normalise = normalise
        if data is not None:
            self.set_data(data, dim_order)

    @property
    def data(self):
        """Return data array."""
        return self._data

    def n_realisations(self, current_value=None):
        """Number of realisations over samples and replications.

        Args:
            current_value : tuple [optional]
                reference point for calculation of number of realisations
                (e.g. when using an embedding of length k, we count
                realisations from the k+1th sample because we loose the first k
                samples to the embedding); if no current_value is provided, the
                number of all samples is used
        """
        return (self.n_realisations_samples(current_value) *
                self.n_realisations_repl())

    def n_realisations_samples(self, current_value=None):
        """Number of realisations over samples.

        Args:
            current_value : tuple [optional]
                reference point for calculation of number of realisations
                (e.g. when using an embedding of length k, the current value is
                at sample k + 1; we thus count realisations from the k + 1st
                sample because we loose the first k samples to the embedding)
        """
        if current_value is None:
            return self.n_samples
        else:
            return self.n_samples - current_value[1]

    def n_realisations_repl(self):
        """Number of realisations over replications."""
        return self.n_replications

    @data.setter
    def data(self, d):
        if hasattr(self, 'data'):
            raise AttributeError('You can not assign a value to this attribute'
                                 ' directly, use the set_data method instead.')
        else:
            self._data = d

    @data.deleter
    def data(self):
        print('overwriting existing data')
        del(self._data)

    def set_data(self, data, dim_order):
        """Overwrite data in an existing Data object.

        Args:
            data : numpy array
                1- to 3-dimensional array of realisations
            dim_order : string
                order of dimensions, accepts any combination of the characters
                'p', 's', and 'r' for processes, samples, and replications;
                must have the same length as number of dimensions in data
        """
        if len(dim_order) > 3:
            raise RuntimeError('dim_order can not have more than three '
                               'entries')
        if len(dim_order) != data.ndim:
            raise RuntimeError('Data array dimension ({0}) and length of '
                               'dim_order ({1}) are not equal.'.format(
                                           data.ndim, len(dim_order)))

        # Bring data into the order processes x samples x replications and set
        # set data.
        data_ordered = self._reorder_data(data, dim_order)
        self._set_data_size(data_ordered)
        print('Adding data with properties: {0} processes, {1} samples, {2} '
              'replications'.format(self.n_processes, self.n_samples,
                                    self.n_replications))
        try:
            delattr(self, 'data')
        except AttributeError:
            pass
        if self.normalise:
            self.data = self._normalise_data(data_ordered)
        else:
            self.data = data_ordered

    def _normalise_data(self, d):
        """Z-standardise data separately for each process."""
        d_standardised = np.empty(d.shape)
        for process in range(self.n_processes):
            s = utils.standardise(
                            d[process, :, :].reshape(1, self.n_realisations()),
                            dimension=1)
            d_standardised[process, :, :] = s.reshape(self.n_samples,
                                                      self.n_replications)
        return d_standardised

    def _reorder_data(self, data, dim_order):
        """Reorder data dimensions to processes x samples x replications."""
        # add singletons for missing dimensions
        missing_dims = 'psr'
        for dim in dim_order:
            missing_dims = missing_dims.replace(dim, '')
        for dim in missing_dims:
            data = np.expand_dims(data, data.ndim)
            dim_order += dim

        # reorder array dims if necessary
        if dim_order[0] != 'p':
            ind_p = dim_order.index('p')
            data = data.swapaxes(0, ind_p)
            dim_order = utils.swap_chars(dim_order, 0, ind_p)
        if dim_order[1] != 's':
            data = data.swapaxes(1, dim_order.index('s'))
        return data

    def _set_data_size(self, data):
        """Set the data size."""
        self.n_processes = data.shape[0]
        self.n_samples = data.shape[1]
        self.n_replications = data.shape[2]

    def _get_data(self, idx_list, current_value, shuffle=False):
        """Return realisations for a list of indices.

        Return realisations for indices in list. Optionally, realisations can
        be shuffled to create surrogate data for statistical testing. For
        shuffling, data blocks are permuted over replications while their
        temporal order stays intact within replications:

        orig:
            repl. index:   1 1 1 1 2 2 2 2 3 3 3 3 4 4 4 4 5 5 5 5 6 6 6 6 ...
            sample index:  1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4 ...

        shuffled:
            repl. index:   3 3 3 3 1 1 1 1 4 4 4 4 6 6 6 6 2 2 2 2 5 5 5 5 ...
            sample index:  1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4 1 2 3 4 ...

        Args:
            idx_list: list of tuples
                variable indices
            current_value : tuple
                index of the current value in current analysis, has to have the
                form (idx process, idx sample)
            shuffle: bool
                if true permute blocks of replications over trials

        Returns:
            numpy array
                realisations with dimensions (no. samples * no.replications) x
                number of indices
            numpy array
                replication index for each realisation with dimensions (no.
                samples * no.replications) x number of indices
        """
        # Check if requested indices are smaller than the current_value.
        if not all(np.array([x[1] for x in idx_list]) <= current_value[1]):
            print('Index list: {0}\ncurrent value: {1}'.format(idx_list,
                                                               current_value))
            raise RuntimeError('All indices for which data is retrieved must '
                               ' be smaller than the current value.')

        # Allocate memory.
        n_real_time = self.n_realisations_samples(current_value)
        n_real_repl = self.n_realisations_repl()
        realisations = np.empty((n_real_time * n_real_repl, len(idx_list)))

        # Shuffle the replication order if requested. This creates surrogate
        # data by permuting replications while keeping the order of samples
        # intact.
        if shuffle:
            replications_order = np.random.permutation(self.n_replications)
        else:
            replications_order = np.arange(self.n_replications)

        # Retrieve data.
        i = 0
        for idx in idx_list:
            r = 0
            last_sample = idx[1] - current_value[1]  # indexing is much faster
            if last_sample == 0:                     # than looping over time!
                last_sample = None
            for replication in replications_order:
                try:
                    realisations[r:r + n_real_time, i] = self.data[
                                                        idx[0],
                                                        idx[1]: last_sample,
                                                        replication]
                except IndexError:
                    raise IndexError('You tried to access variable {0} in a '
                                     'data set with {1} processes and {2} '
                                     'samples.'.format(idx, self.n_processes,
                                                       self.n_samples))
                r += n_real_time

            assert(not np.isnan(realisations[:, i]).any()), ('There are nans '
                                                             'in the retrieved'
                                                             ' realisations.')
            i += 1

        # For each realisation keep the index of the replication it came from.
        replications_index = np.repeat(replications_order, n_real_time)
        assert(replications_index.shape[0] == realisations.shape[0]), (
               'There seems to be a problem with the replications index.')

        return realisations, replications_index

    def get_realisations(self, current_value, idx_list):
        """Return all realisations of a random variable in the data.

        Return realisations of random variables represented by a list of
        indices. An index is expected to have the form (process index, sample
        index). The analysis_setup contains information like for example the
        current_value in TE analysis, which are needed to identify variable
        realisations in the raw data.

        Args:
            current_value : tuple
                index of the current_value in the data
            idx_list : list of tuples
                indices of variables

        Returns:
            numpy array
                realisations with dimensions replications x number of indices
            numpy array
                replication index for each realisation

        Raises:
            TypeError
                If idx is not a list
        """
        if type(idx_list) is not list:
            raise TypeError('idx_realisations must be a list of tuples.')
        return self._get_data(idx_list, current_value, shuffle=False)

    def permute_replications(self, current_value, idx_list):
        """Return realisations with permuted replications (time stays intact).

        Create surrogate data by permuting realisations over replications while
        keeping the temporal structure (order of samples) intact. Return
        realisations for all indices in the list, where an index is expected to
        have the form (process index, sample index). Realisations are permuted
        block-wise by permuting the order of replications:

        original data:
            rep.:   1 1 1 1  2 2 2 2  3 3 3 3  4 4 4 4  5 5 5 5  6 6 6 6 ...
            sample: 1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4 ...

        permuted data:
            rep.:   3 3 3 3  1 1 1 1  4 4 4 4  6 6 6 6  2 2 2 2  5 5 5 5 ...
            sample: 1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4 ...

        Args:
            current_value : tuple
                index of the current_value in the data
            idx_list : list of tuples
                indices of variables

        Returns:
            numpy array
                permuted realisations with dimensions replications x number of
                indices
            numpy array
                replication index for each realisation

        Raises:
            TypeError if idx_realisations is not a list
        """
        if type(idx_list) is not list:
            raise TypeError('idx needs to be a list of tuples.')
        return self._get_data(idx_list, current_value, shuffle=True)

    def permute_samples(self, current_value, idx_list, perm_range='max'):
        """Return realisations with permuted samples (repl. stays intact).

        Create surrogate data by permuting realisations over samples (time)
        while keeping the order of replications intact. Return realisations for
        all indices in the list, where an index is expected to have the form
        (process index, sample index). Realisations are permuted sample-wise or
        within a permutation range (perm_range). If no permutation range is
        given, samples are randomly permuted over the whole replication, i.e.,
        over all time indices in the replication:

        original data:
            rep.:   1 1 1 1  2 2 2 2  3 3 3 3  4 4 4 4  5 5 5 5  6 6 6 6 ...
            sample: 1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4  1 2 3 4 ...

        permuted data (perm_range='max'):
            rep.:   1 1 1 1  2 2 2 2  3 3 3 3  4 4 4 4  5 5 5 5  6 6 6 6 ...
            sample: 4 1 3 2  1 3 4 2  4 3 2 1  1 2 4 3  2 4 3 1  1 3 4 2 ...

        permuted data (perm_range=2):
            rep.:   1 1 1 1  2 2 2 2  3 3 3 3  4 4 4 4  5 5 5 5  6 6 6 6 ...
            sample: 2 1 3 4  1 2 4 3  2 1 4 3  1 2 3 4  2 1 4 3  1 2 4 3 ...

        Args:
            current_value : tuple
                index of the current_value in the data
            idx_list : list of tuples
                indices of variables
            perm_range : int or 'max' [optional]
                range over which realisations are permuted, if 'max'
                realisations are permuted over the whole replication, otherwise
                realisations are permuted over blocks of length perm_range

        Returns:
            numpy array
                permuted realisations with dimensions replications x number of
                indices
            numpy array
                sample index for each realisation

        Raises:
            TypeError if idx_realisations is not a list

        Note:
            This permutation scheme is the fall-back option if the number of
            replications is too small to allow a sufficient number of
            permutations for the generation of surrogate data.
        """
        [realisations, replication_idx] = self.get_realisations(current_value,
                                                                idx_list)

        realisations_perm = cp.copy(realisations)
        n_per_repl = sum(replication_idx == 0)
        if type(perm_range) is not str:
            assert (perm_range > 1), ('Permutation range has to be larger '
                                      'than 1 otherwise there is nothing to '
                                      'permute.')
        else:
            if perm_range == 'max':
                perm_range = n_per_repl
            else:
                raise ValueError('Unkown value for "perm_range": {0}'.format(
                    perm_range))
        assert (replication_idx.shape[0] == realisations.shape[0]), (
                'Array "replication" index must have as many entries as the '
                'first dimension of array "realisations".')

        assert (n_per_repl >= perm_range), ('Not enough realisations per '
                                            'replication ({0}) to allow for '
                                            'the requested "perm_range" ({1}).'
                                            .format(n_per_repl, perm_range))

        # Create a permutation of the data that respects the requested permutation
        # range and can be applied to the realisations from each replication in
        # turn.
        if perm_range == n_per_repl:  # permute all realisations in one replication
            perm = np.random.permutation(n_per_repl)
        else:  # build a permutation that permutes only within the perm_range
            perm = np.empty(n_per_repl, dtype=int)
            remainder = n_per_repl % perm_range
            i = 0
            for p in range(n_per_repl // perm_range):
                perm[i:i + perm_range] = np.random.permutation(perm_range) + i
                i += perm_range
            if remainder > 0:
                perm[-remainder:] = np.random.permutation(remainder) + i

        # Apply the permutation to data from each replication, individually.
        perm_idx = np.empty(realisations_perm.shape[0])
        for replication in range(self.n_replications):
            mask = replication_idx == replication
            d = realisations_perm[mask, :]
            realisations_perm[mask, :] = d[perm, :]
            perm_idx[mask] = perm

        return realisations_perm, perm_idx

    def generate_mute_data(self, n_samples=1000, n_replications=10):
        """Generate example data for a 5-process network.

        Generate example data and overwrite the instance's current data. The
        network is used as an example the paper on the MuTE toolbox (Montalto,
        PLOS ONE, 2014, eq. 14). The network consists of five autoregressive
        (AR) processes with model orders 2 and les and the following
        (non-linear) couplings:

        0 -> 1, u = 2
        0 -> 2, u = 3
        0 -> 3, u = 2 (non-linear)
        3 -> 4, u = 1
        4 -> 3, u = 1

        Args:
            n_samples : int
                number of samples simulated for each process and replication
            n_replications : int
                number of replications
        """
        n_processes = 5
        n_samples = n_samples
        n_replications = n_replications

        x = np.zeros((n_processes, n_samples + 3,
                      n_replications))
        x[:, 0:3, :] = np.random.normal(size=(n_processes, 3,
                                              n_replications))
        term_1 = 0.95 * np.sqrt(2)
        term_2 = 0.25 * np.sqrt(2)
        term_3 = -0.25 * np.sqrt(2)
        for r in range(n_replications):
            for n in range(3, n_samples + 3):
                x[0, n, r] = (term_1 * x[0, n - 1, r] -
                              0.9025 * x[0, n - 2, r] + np.random.normal())
                x[1, n, r] = 0.5 * x[0, n - 2, r] ** 2 + np.random.normal()
                x[2, n, r] = -0.4 * x[0, n - 3, r] + np.random.normal()
                x[3, n, r] = (-0.5 * x[0, n - 2, r] ** 2 +
                              term_2 * x[3, n - 1, r] +
                              term_2 * x[4, n - 1, r] +
                              np.random.normal())
                x[4, n, r] = (term_3 * x[3, n - 1, r] +
                              term_2 * x[4, n - 1, r] +
                              np.random.normal())
        self.set_data(x[:, 3:, :], 'psr')

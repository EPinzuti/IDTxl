import types
import random
import math as math
import numpy as np
from . import estimators_te
from . import estimators_cmi
from . import estimators_mi


class Estimator(object):
    """Set the estimator requested by the user."""

    @classmethod
    def removeMethod(cls, name):
        return delattr(cls, name)

    @classmethod
    def addMethodAs(cls, func, new_name=None):
        if new_name is None:
            new_name = func.__name__
        return setattr(cls, new_name, types.MethodType(func, cls))

    def __init__(self):
        self.addMethodAs(is_parallel, "is_parallel")

    def get_estimator(self):
        return self.estimator_name

    def estimate_mult(self, n_chunks=1, options=None, re_use=None, **data):
        """Estimate measure for multiple data sets (chunks).

        Test if the estimator used provides parallel capabilities; if so, 
        estimate measure for multiple data sets ('chunks') in parallel. 
        Otherwise, iterate over individual chunks.

        The number of variables in data depends on the measure to be estimated, 
        e.g., 2 for mutual information and 3 for TE.

        Each entry in data should be a numpy array with realisations, where the
        first axis is assumed to represent realisations (over chunks), while 
        the second axis is the variable dimension. 

        Each numpy array with realisations can hold either the realisations for 
        multiple chunks or can hold the realisation for a single chunk, which 
        gets replicated for parallel estimation and gets re-used for iterative
        estimation, in order to save memory. The variables for re-use are 
        provided in re-use as list of dictionary keys indicating entries in 
        data for re-use.

        Args:
            self : instance of Estimator_cmi            
            n_chunks : int
                number of data chunks
            options : dict
                sets estimation parameters
            re_use : list of keys
                realisatins to be re-used
            data: dict of numpy arrays
                realisations of random random variables 

        Returns:
            numpy array of estimated values for each data set
        """
        if re_use is None:
            re_use = []

        if self.is_parallel(self.estimator_name):
            for k in re_use:
                data[k] = np.tile(data[k], (n_chunks, 1))
            return self.estimate(self, **data, n_chunks=1, opts=options)  # TODO check order of arguments, change that also in the called function      
        
        else:  # cut data into chunks and estimate iteratively          
            chunk_size = data[data.keys()[0]].shape[0] / n_chunks
            idx_1 = 0
            idx_2 = chunk_size
            res = np.empty((n_chunks))            
            slice_vars = list(set(data.keys()).difference(set(re_use)))
            i = 0
            for c in range(n_chunks):
                chunk_data = {}
                for k in slice_vars:  # NOTE: I AM NOT CREATING A DEEP COPY HERE!
                    chunk_data[k] = data[k][idx_1:idx_2, :]
                for k in re_use:
                    chunk_data[k] = data[k]
                res[i] = self.estimate(self, **chunk_data, opts=options)  # TODO check order of arguments, change that also in the called function      
                idx_1 = idx_2
                idx_2 += chunk_size
                i += 1

            return res


class Estimator_te(Estimator):
    """Set the requested transfer entropy estimator."""

    def __init__(self, estimator_name):
        try:
            estimator = getattr(estimators_te, estimator_name)
        except AttributeError:
            raise AttributeError('The requested TE estimator "{0}" was not '
                                 'found.'.format(estimator_name))
        else:
            self.estimator_name = estimator_name
            self.addMethodAs(estimator, "estimate")
        super().__init__()


class Estimator_cmi(Estimator):
    """Set the requested conditional mutual information estimator."""

    def __init__(self, estimator_name):
        try:
            estimator = getattr(estimators_cmi, estimator_name)
        except AttributeError:
            raise AttributeError('The requested CMI estimator "{0}" was not '
                                 'found.'.format(estimator_name))
        else:
            self.estimator_name = estimator_name
            self.addMethodAs(estimator, "estimate")
        super().__init__()


class Estimator_mi(Estimator):
    """Set the requested mutual information estimator."""

    def __init__(self, estimator_name):
        try:
            estimator = getattr(estimators_mi, estimator_name)
        except AttributeError:
            raise AttributeError('The requested MI estimator "{0}" was not '
                                 'found.'.format(estimator_name))
        else:
            self.estimator_name = estimator_name
            self.addMethodAs(estimator, "estimate")
        super().__init__()


if __name__ == "__main__":
    """ Do a quick check if everything is called correctly."""

    te_estimator = Estimator_te("jidt_kraskov")
    mi_estimator = Estimator_mi("jidt_kraskov")
    cmi_estimator = Estimator_cmi("jidt_kraskov")

    n_obs = 10000
    covariance = 0.4
    dim = 5
    source = [random.normalvariate(0, 1) for r in range(n_obs)]
    target = [0] + [sum(pair) for pair in zip(
                    [covariance * y for y in source[0:n_obs-1]],
                    [(1-covariance) * y for y in [
                        random.normalvariate(0, 1) for r in range(n_obs-1)]])]
    var1 = [[random.normalvariate(0, 1) for x in range(dim)] for
            x in range(n_obs)]
    var2 = [[random.normalvariate(0, 1) for x in range(dim)] for
            x in range(n_obs)]
    conditional = [[random.normalvariate(0, 1) for x in range(dim)] for
                   x in range(n_obs)]

    knn = 4
    history_length = 1
    options = {
        'kraskov_k': 4,
        'history_target': 3
        }

    te = te_estimator.estimate(np.array(source), np.array(target), options)
    expected_te = math.log(1 / (1 - math.pow(covariance, 2)))
    print('TE estimator is {0}'.format(te_estimator.get_estimator()))
    print('TE result: {0:.4f} nats; expected to be close to {1:.4f} nats '
          'for correlated Gaussians.'.format(te, expected_te))

    mi = mi_estimator.estimate(np.array(var1), np.array(var2), options)
    print('MI estimator is ' + mi_estimator.get_estimator())
    print('MI result: %.4f nats.' % mi)

    cmi = cmi_estimator.estimate(np.array(var1), np.array(var2),
                                 np.array(conditional), options)
    print('Estimator is ' + cmi_estimator.get_estimator())
    print('CMI result: %.4f nats.' % cmi)

    # CMI testcases with correlated variables
    # Generate some random normalised data.

    # set options for maximal comparability between JIDT and opencl
    #options = {
    #    'kraskov_k': 4, 'noise_level': 0, 'debug': True, 'theiler_t': 0
    #    }

    numObservations = 10000
    covariance = 0.4

    # Source array of random normals:
    var1 = np.random.randn(numObservations, 1)
    # Destination array of random normals with partial correlation to previous
    # value of sourceArray
    var2 = [sum(pair) for pair in zip([covariance*y for y in var1],
            [(1-covariance)*y for y in
            [random.normalvariate(0, 1) for r in range(numObservations)]])]
    var2 = np.array(var2)
    # Uncorrelated conditionals:
    conditional = np.random.randn(numObservations, 1)

    # casting data to single and back for comparison with single precision
    # computations on the GPU
    cmi_jidt = cmi_estimator.estimate(np.array(var1).astype('float32').astype('float64'),
                                 np.array(var2).astype('float32').astype('float64'),
                                 np.array(conditional).astype('float32').astype('float64'),
                                 options)
    print('Estimator is ' + cmi_estimator.get_estimator())
#    print('CMI result: %.4f nats.' % cmi)
    print("CMI result %.4f nats; expected to be close to %.4f nats for these correlated Gaussians" % \
          (cmi_jidt, math.log(1/(1-math.pow(covariance, 2)))))

#    # casting data to single and back for comparison with single precision
#    # computations on the GPU
#    mi_jidt = mi_estimator.estimate(np.array(var1).astype('float32').astype('float64'),
#                                 np.array(var2).astype('float32').astype('float64'),
#                                 options)
#    print('Estimator is ' + mi_estimator.get_estimator())
#    print("MI result %.4f nats; expected to be close to %.4f nats for these correlated Gaussians" % \
#          mi_jidt, math.log(1/(1-math.pow(covariance, 2))))


    cmi_estimator = Estimator_cmi("opencl_kraskov")
    cmi_ocl = cmi_estimator.estimate(np.array(var1), np.array(var2),
                                 np.array(conditional), options)
    print('Estimator is ' + cmi_estimator.get_estimator())
    print('CMI result: %.4f nats.' % cmi_ocl)

    assert int(cmi_jidt*10000) == int(cmi_ocl*10000) , "JIDT and opencl estmator results mismatch"


    mi_estimator = Estimator_mi("opencl_kraskov")
    mi_ocl = mi_estimator.estimate(np.array(var1), np.array(var2), options)
    print('Estimator is ' + mi_estimator.get_estimator())
    print('MI result: %.4f nats.' % mi_ocl)

#    assert int(mi_jidt*10000) == int(mi_ocl*10000) , "JIDT and opencl estmator results mismatch"

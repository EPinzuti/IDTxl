import random as rn
import numpy as np
from idtxl.set_estimator import Estimator_ais


def test_ais_gaussian():
    """Test multivariate TE estimation on correlated Gaussians.

    Run the multivariate TE algorithm on two sets of random Gaussian data with
    a given covariance. The second data set is shifted by one sample creating
    a source-target delay of one sample. This example is modeled after the
    JIDT demo 4 for transfer entropy. The resulting TE can be compared to the
    analytical result (but expect some error in the estimate).

    Note:
        This test runs considerably faster than other system tests.
        This produces strange small values for non-coupled sources.  TODO
    """
    n = 1000
    source = [rn.normalvariate(0, 1) for r in range(n)]  # correlated src
    # Cast everything to numpy so the idtxl estimator understands it.
    source = np.array(source)

    analysis_opts = {
        'kraskov_k': 4,
        'normalise': 'false',
        'theiler_t': 0,
        'noise_level': 1e-8,
        'local_values': False,
        'tau': 1,
        'history': 1,
        }
    ais_est = Estimator_ais('jidt_kraskov')
    ais = ais_est.estimate(source, analysis_opts)
    print('AIS for random normal data without memory (calling estimator '
          'directly, expected is something close to 0): {0}'.format(ais))


def test_ais_local_values():
    """Test local AIS estimation."""
    n = 1000
    source = [rn.normalvariate(0, 1) for r in range(n)]
    analysis_opts = {
        'kraskov_k': 4,
        'normalise': 'false',
        'theiler_t': 0,
        'noise_level': 1e-8,
        'local_values': True,
        'history': 3,
        }
    ais_est = Estimator_ais('jidt_kraskov')
    ais_res = ais_est.estimate(np.array(source),
                               analysis_opts)
    assert ais_res.shape[0] == n, 'Local AIS estimator did not return an array'

if __name__ == '__main__':
    test_ais_local_values()
    test_ais_gaussian()

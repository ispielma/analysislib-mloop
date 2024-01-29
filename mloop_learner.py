from mloop.learners import Learner
import mloop.utilities as mlu

import threading
import logging
import queue
import time
import numpy as np

logger = logging.getLogger('analysislib_mloop')

class SimpleRandomLearner(Learner, threading.Thread):
    '''
    Random learner. Simply generates new parameters randomly with a uniform distribution over the boundaries. Learner is perhaps a misnomer 
    for this class.  Unlike the M-loop version, this complexly ignores the cost sent to it.  Its only job is to make sure that its queue is non-empty.

    Args:
        **kwargs (Optional dict): Other values to be passed to Learner.

    Keyword Args:
        min_boundary (Optional [array]): If set to None, overrides default learner values and sets it to a set of value 0. Default None.
        max_boundary (Optional [array]): If set to None overides default learner values and sets it to an array of value 1. Default None.
        first_params (Optional [array]): The first parameters to test. If None will just randomly sample the initial condition.
        trust_region (Optional [float or array]): The trust region defines the maximum distance the learner will travel from the current best set of parameters. If None, the learner will search everywhere. If a float, this number must be between 0 and 1 and defines maximum distance the learner will venture as a percentage of the boundaries. If it is an array, it must have the same size as the number of parameters and the numbers define the maximum absolute distance that can be moved along each direction.
    '''

    def __init__(self,
                 trust_region=None,
                 first_params=None,
                 **kwargs):

        super(SimpleRandomLearner,self).__init__(**kwargs)

        if ((np.all(np.isfinite(self.min_boundary))&np.all(np.isfinite(self.max_boundary)))==False):
            msg = 'Minimum and/or maximum boundaries are NaN or inf. Must both be finite for random learner. Min boundary:' + repr(self.min_boundary) +'. Max boundary:' + repr(self.max_boundary)
            self.log.error(msg)
            raise ValueError(msg)
        if first_params is None:
            self.first_params = None
            self.log.debug("First parameters not provided.")
        else:
            self.first_params = np.array(first_params, dtype=float)

            if not self.check_num_params(self.first_params):
                msg = 'first_params has the wrong number of parameters:' + repr(self.first_params)
                self.log.error(msg)
                raise ValueError(msg)
            elif not self.check_in_boundary(self.first_params):
                msg = 'first_params is not in the boundary:' + repr(self.first_params)
                self.log.error(msg)
                raise ValueError(msg)
            else:
                msg = 'first_params are:' + repr(self.first_params)
                self.log.debug(msg)


        # Keep track of best parameters to implement trust region.
        self.best_cost = None
        self.best_parameters = None

        if trust_region is not None:
            trust_region = None
            self.log.info("Trust region is ignored in Simple Random Learner")
        self._set_trust_region(trust_region)

        new_values_dict = {
            'archive_type': 'random_learner',
            'trust_region': self.trust_region,
            'has_trust_region': self.has_trust_region,
        }
        self.archive_dict.update(new_values_dict)

        self.log.debug('Simple random learner init completed.')

    def run(self):
        '''
        Puts the next parameters on the queue which are randomly picked from a uniform distribution between the minimum and maximum boundaries when a cost is added to the cost queue.
        '''
        if self.first_params is None:
            self.log.debug('Starting Simple Random Learner with random starting parameters')
            next_params = mlu.rng.uniform(self.min_boundary, self.max_boundary)
        else:
            self.log.debug('Starting Simple Random Learner with provided starting parameters')
            next_params = self.first_params

        while not self.end_event.is_set():

            # Wait until the queue is empty and send a new element promptly.
            while not self.params_out_queue.empty():
                time.sleep(self.learner_wait)

            self.params_out_queue.put(next_params)

            # Clear the costs in queue
            try:
                while True:
                    self.costs_in_queue.get_nowait()
            except queue.Empty:
                pass

            next_params =  mlu.rng.uniform(self.min_boundary, self.max_boundary)

        self._shut_down()
        self.log.debug('Ended Simple Random Learner')
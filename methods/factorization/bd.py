from operator import div
from scipy.special import erfc, erfcinv

import models.nmf_std as mstd
import models.mf_fit as mfit
import models.mf_track as mtrack
from utils.linalg import *

class Bd(mstd.Nmf_std):
    """
    Bayesian Decomposition (BD) - Bayesian nonnegative matrix factorization Gibbs sampler [16].
    
    In the Bayesian framework knowledge of the distribution of the residuals is stated in terms of likelihood function and
    the parameters in terms of prior densities. In this method normal likelihood and exponential priors are chosen as these 
    are suitable for a wide range of problems and permit an efficient Gibbs sampling procedure. Using Bayes rule, the posterior
    can be maximized to yield an estimate of basis (W) and mixture (H) matrix. However, we are interested in estimating the 
    marginal density of the factors and because the marginals cannot be directly computed by integrating the posterior, an
    MCMC sampling method is used.    
    
    In Gibbs sampling a sequence of samples is drawn from the conditional posterior densities of the model parameters and this
    converges to a sample from the joint posterior. The conditional densities of basis and mixture matrices are proportional 
    to a normal multiplied by an exponential, i. e. rectified normal density. The conditional density of sigma**2 is an inverse 
    Gamma density. The posterior can be approximated by sequentially sampling from these conditional densities. 
    
    Bayesian NMF is concerned with the sampling from the posterior distribution of basis and mixture factors. Algorithm outline
    is: 
        #. Initialize basis and mixture matrix. 
        #. Sample from rectified Gaussian for each column in basis matrix.
        #. Sample from rectified Gaussian for each row in mixture matrix. 
        #. Sample from inverse Gamma for noise variance
        #. Repeat the previous three steps until some convergence criterion is met. 
        
    The sampling procedure could be used for estimating the marginal likelihood, which is useful for model selection, i. e. 
    choosing factorization rank. 
    
    [16] Schmidt, M.N., Winther, O.,  and Hansen, L.K., (2009). Bayesian Non-negative Matrix Factorization. 
        In Proceedings of ICA. 2009, 540-547.
    """

    def __init__(self, **params):
        """
        For detailed explanation of the general model parameters see :mod:`mf_methods`.
        
        If :param:`max_iter` of the underlying model is not specified, default value of :param:`max_iter` 30 is set. The
        meaning of :param:`max_iter` for BD is the number of Gibbs samples to compute. Sequence of Gibbs samples converges
        to a sample from the joint posterior. 
        
        The following are algorithm specific model options which can be passed with values as keyword arguments.
        
        :param alpha: The prior for basis matrix (W) of proper dimensions. Default is zeros matrix prior.
        :type alpha: :class:`scipy.sparse.csr_matrix` or :class:`numpy.matrix`
        :param beta: The prior for mixture matrix (H) of proper dimensions. Default is zeros matrix prior.
        :type beta: :class:`scipy.sparse.csr_matrix` or :class:`numpy.matrix`
        :param theta: The prior for :param:`sigma`. Default is 0.
        :type theta: `float`
        :param k: The prior for :param:`sigma`. Default is 0. 
        :type k: `float`
        :param sigma: Initial value for noise variance (sigma**2). Default is 1. 
        :type sigma: `float`  
        :param skip: Number of initial samples to skip. Default is 100.
        :type skip: `int`
        :param stride: Return every :param:`stride`'th sample. Default is 1. 
        :type stride: `int`
        :param n_w: Method does not sample from these columns of basis matrix. Column i is not sampled if :param:`n_w`[i] is True. 
                    Default is sampling from all columns. 
        :type n_w: :class:`numpy.ndarray` or list with shape (factorization rank, 1) with logical values
        :param n_h: Method does not sample from these rows of mixture matrix. Row i is not sampled if :param:`n_h`[i] is True. 
                    Default is sampling from all rows. 
        :type n_h: :class:`numpy.ndarray` or list with shape (factorization rank, 1) with logical values
        :param n_sigma: Method does not sample from :param:`sigma`. By default sampling is done. 
        :type n_sigma: logical    
        """
        self.name = "bd"
        self.aseeds = ["random", "fixed", "nndsvd", "random_c", "random_vcol"]
        mstd.Nmf_std.__init__(self, params)
        
    def factorize(self):
        """
        Compute matrix factorization.
         
        Return fitted factorization model.
        """
        self._set_params()
        self.v = multiply(self.V, self.V).sum() / 2.
                
        for _ in xrange(self.n_run):
            self.W, self.H = self.seed.initialize(self.V, self.rank, self.options)
            pobj = cobj = self.objective()
            iter = 0
            while self._is_satisfied(pobj, cobj, iter):
                pobj = cobj
                self.update(iter)
                cobj = self.objective() if not self.test_conv or iter % self.test_conv == 0 else cobj
                iter += 1
            if self.callback:
                self.final_obj = cobj
                mffit = mfit.Mf_fit(self) 
                self.callback(mffit)
            if self.tracker != None:
                self.tracker.add(W = self.W.copy(), H = self.H.copy(), sigma = self.sigma)
        
        self.n_iter = iter - 1
        self.final_obj = cobj
        mffit = mfit.Mf_fit(self)
        return mffit
        
    def _is_satisfied(self, pobj, cobj, iter):
        """Compute the satisfiability of the stopping criteria based on stopping parameters and objective function value."""
        if self.max_iter and self.max_iter < iter:
            return False
        if self.min_residuals and iter > 0 and cobj - pobj <= self.min_residuals:
            return False
        if iter > 0 and cobj >= pobj:
            return False
        return True
    
    def _set_params(self):
        if not self.max_iter: self.max_iter = 30
        self.alpha = self.options.get('alpha', sp.csr_matrix((self.V.shape[0], self.rank)))
        self.beta = self.options.get('beta', sp.csr_matrix((self.rank, self.V.shape[1])))
        self.theta = self.options.get('theta', .0)
        self.k = self.options.get('k', .0)
        self.sigma = self.options.get('sigma', 1.) 
        self.skip = self.options.get('skip', 100) 
        self.stride = self.options.get('stride', 1)  
        self.n_w = self.options.get('n_w', np.zeros((self.rank, 1)))
        self.n_h = self.options.get('n_h', np.zeros((self.rank, 1)))
        self.n_sigma = self.options.get('n_sigma', 0)
        self.tracker = mtrack.Mf_track() if self.options.get('track', 0) and self.n_run > 1 else None
        
    def update(self, iter):
        """Update basis and mixture matrix."""
        for _ in xrange(self.skip * (iter == 0) + self.stride * (iter > 0)):
            # update basis matrix
            C = dot(self.H, self.H.T)
            D = dot(self.V, self.H.T)
            for n in xrange(self.rank):
                if not self.n_w[n]:
                    nn = list(xrange(n - 1)) + list(xrange(n, self.rank))
                    temp = self._randr(sop(D[:, n] - dot(self.W[:, nn], C[nn, n]), C[n, n], div), self.sigma / C[n, n], self.alpha[:, n])
                    for j in xrange(self.W.shape[0]):
                        self.W[j, n] = temp[j]
            # update sigma
            if not self.n_sigma:
                self.sigma = 1. / np.random.gamma(shape = (self.V.shape[0] * self.V.shape[1]) / 2. + 1. + self.k, 
                                                  scale = 1. / (self.theta + self.v + multiply(self.W, dot(self.W, C) - 2 * D).sum() / 2.))
            # update mixture matrix
            E = dot(self.W.T, self.W)
            F = dot(self.W.T, self.V)
            for n in xrange(self.rank):
                if not self.n_h[n]:
                    nn = list(xrange(n - 1)) + list(xrange(n, self.rank))
                    temp = self._randr(sop(F[n, :] - dot(E[n, nn], self.H[nn, :]), E[n, n], div), self.sigma / E[n, n], self.beta[n, :].T)
                    for j in xrange(self.H.shape[1]):
                        self.H[n, j] = temp[j]
                    
    def _randr(self, m, s, l):    
        """Return random number from p(x)=K*exp(-(x-m)^2/s-l'x), x>=0."""
        # m and l are vectors and s is scalar
        m = m.toarray() if sp.isspmatrix(m) else np.array(m)
        l = l.toarray() if sp.isspmatrix(l) else np.array(l)
        A = (l * s - m) / sqrt(2 * s)
        a = A > 26.
        x = np.zeros(m.shape)
        y = np.random.rand(m.shape[0], m.shape[1])
        x[a] = - np.log(y[a]) / ((l[a] * s - m[a]) / s)
        a = np.array(1 - a, dtype = bool)
        R = erfc(abs(A[a]))
        x[a] = erfcinv(y[a] * R - (A[a] < 0) * (2 * y[a] + R - 2)) * sqrt( 2 * s) + m[a] - l[a] * s
        x[np.isnan(x)] = 0
        x[x < 0] = 0
        x[np.isinf(x)] = 0
        return x.real
    
    def objective(self):
        """Compute squared Frobenius norm of a target matrix and its NMF estimate.""" 
        return (sop(self.V - dot(self.W, self.H), 2, pow)).sum()
    
    def __str__(self):
        return self.name
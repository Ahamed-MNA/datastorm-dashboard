import numpy as np
import pandas as pd
from scipy.optimize import minimize
from scipy.special import log_ndtr
import logging

logger = logging.getLogger(__name__)

def sfa_log_likelihood(params, X, y):
    k = X.shape[1]
    beta = params[:k]
    sigma_u = np.exp(params[k])
    sigma_v = np.exp(params[k+1])
    
    sigma_sq = sigma_u**2 + sigma_v**2
    sigma = np.sqrt(sigma_sq)
    lam = sigma_u / sigma_v
    
    epsilon = y - np.dot(X, beta)
    
    term1 = np.log(2/sigma)
    z = epsilon / sigma
    term2 = -0.9189385332046727 - 0.5 * (z**2)
    term3 = log_ndtr(-z * lam)
    
    ll = np.sum(term1 + term2 + term3)
    return -ll

class SFAModel:
    def __init__(self):
        self.beta = None
        self.sigma_u = None
        self.sigma_v = None
        self.feature_names = None

    def fit(self, X, y, verbose=True):
        self.feature_names = X.columns.tolist()
        X_val = X.values
        y_val = y.values
        
        k = X_val.shape[1]
        initial_beta = np.linalg.lstsq(X_val, y_val, rcond=None)[0]
        initial_params = np.concatenate([initial_beta, [0.1, 0.1]])
        
        logger.info(f"Starting SFA optimization for {k} features...")
        
        iteration = 0
        def callback(xk):
            nonlocal iteration
            iteration += 1
            if verbose:
                ll_val = sfa_log_likelihood(xk, X_val, y_val)
                logger.info(f"Iteration {iteration:03d}: Neg Log-Likelihood = {ll_val:.4f}")
        
        res = minimize(sfa_log_likelihood, initial_params, args=(X_val, y_val), method='L-BFGS-B', callback=callback)
        
        if res.success:
            self.beta = res.x[:k]
            self.sigma_u = np.exp(res.x[k])
            self.sigma_v = np.exp(res.x[k+1])
            logger.info("SFA Model fitted successfully.")
        else:
            logger.error(f"SFA Optimization failed: {res.message}")
            raise Exception("Model fitting failed.")

    def predict_potential(self, X):
        X_val = X.values
        ln_y_potential = np.dot(X_val, self.beta)
        y_potential = np.exp(ln_y_potential) * np.exp(0.5 * self.sigma_v**2)
        return y_potential

    def get_efficiency(self, X, y_actual):
        potential = self.predict_potential(X)
        efficiency = y_actual / potential
        return efficiency

    def save(self, filepath):
        import pickle
        with open(filepath, 'wb') as f:
            pickle.dump(self, f)
        logger.info(f"Model saved successfully to {filepath}")

    @classmethod
    def load(cls, filepath):
        import pickle
        with open(filepath, 'rb') as f:
            model = pickle.load(f)
        logger.info(f"Model loaded successfully from {filepath}")
        return model

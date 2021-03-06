# -*- coding: utf-8 -*-
'''
Created on 2013-07-31

@author: Yi Li

pyloh.model.poisson_model

================================================================================

Modified on 2014-04-21

@author: Yi Li\
'''
import sys

import numpy as np


from pSCNAClonal.model.model_base import *
from pSCNAClonal.model.utils import *
from pSCNAClonal.preprocess.data.elements import *
from pSCNAClonal.preprocess.data.pools import *

class JointProbabilisticModel(ProbabilisticModel):
    def __init__(self, max_copynumber, subclone_num, baseline_thred):
        ProbabilisticModel.__init__(self, max_copynumber, subclone_num, baseline_thred)

    def read_priors(self, priors_filename):
        if priors_filename != None:
            self.priors_parser.read_priors(priors_filename, self.max_copynumber)
            self.priors = self.priors_parser.priors
        else:
            self.priors = {}
            self.priors['omega'] = np.array(get_omega(self.max_copynumber))*1.0

    # def preprocess(self):
        # #self.data.get_LOH_frac()
        # 这个函数用来计算baseline，所以此处没有用
        # self.data.get_LOH_status(self.baseline_thred)
        # self.data.compute_Lambda_S()

    def _init_components(self):
        self.model_trainer_class = JointModelTrainer
        self.priors = {}


class JointModelTrainer(ModelTrainer):
    def __init__(self, priors, stripePool, max_copynumber, subclone_num, max_iters, stop_value):
        ModelTrainer.__init__(self, priors, stripePool, max_copynumber, subclone_num, max_iters, stop_value)

    def _init_components(self):
        self.config_parameters = JointConfigParameters(self.max_copynumber, self.subclone_num)

        self.model_parameters = JointModelParameters(self.priors, self.stripePool, self.config_parameters)

        self.latent_variables = JointLatentVariables(self.stripePool, self.config_parameters)

        self.model_likelihood = JointModelLikelihood(self.priors, self.stripePool, self.config_parameters)

    def train(self):
        ll_lst = []
        model_parameters_lst = []
        latent_variables_lst = []

        phi_init_lst = get_phi_init(self.subclone_num)

        for phi_init in phi_init_lst:
            phi_init = np.array(phi_init)

            ll, model_parameters, latent_variables = self.train_reinit(phi_init)

            ll_lst.append(ll)
            model_parameters_lst.append(model_parameters)
            latent_variables_lst.append(latent_variables)

        ll_lst = np.array(ll_lst)
        idx_optimum = ll_lst.argmax()

        ll_optimum = ll_lst[idx_optimum]
        model_parameters_optimum = model_parameters_lst[idx_optimum]
        latent_variables_optimum = latent_variables_lst[idx_optimum]

        self.model_parameters.copy_parameters(model_parameters_optimum)
        self.latent_variables.copy_latent_variables(latent_variables_optimum)
        self.ll = ll_optimum

    # the EM step
    def train_reinit(self, phi_init):
        converged = False

        self.model_parameters.reinit_parameters(phi_init)
        ll_old = self.likelihood() # calculate the original log_likelihood
        iters = 0
        phi_list = []
        new_ll_list = []
        while not converged:  # loop until coverage
            self._E_step()  # E step
            self._M_step()  # M step

            parameters = self.model_parameters.parameters
            ll_new = self.likelihood() # ll -> log-likelihood

            if iters > 0:
                ll_change = (ll_new - ll_old) / np.abs(ll_old)
            else:
                ll_change = float('inf')

            self._print_running_info(ll_new, ll_old, ll_change, phi_init, iters)
            phi = self.model_parameters.parameters['phi'].tolist()
            if phi in phi_list:
                new_ll_list[phi_list.index(phi)] = ll_new
            else:
                phi_list.append(phi)
                new_ll_list.append(ll_new)

            ll_old = ll_new

            # if the ll_change is small enough then stop the loop
            if np.abs(ll_change) < self.stop_value:
                print "Stop value of EM iterations exceeded. Exiting training..."
                sys.stdout.flush()
                converged = True

            # or if the number of iterations is greater than the max_iters
            if iters >= self.max_iters:
                print "Maximum numbers of EM iterations exceeded. Exiting training..."
                sys.stdout.flush()
                converged = True

            iters += 1

        model_parameters = JointModelParameters(self.priors, self.stripePool, self.config_parameters)
        model_parameters.copy_parameters(self.model_parameters)
        latent_variables = JointLatentVariables(self.stripePool, self.config_parameters)
        latent_variables.copy_latent_variables(self.latent_variables)

        def write_to_file(phi_list,ll_new_list):
            file = open("plot_data/mdoel_plot_data.txt","wr")
            n = len(phi_list[0])
            file.write("#Estimated subclone prevalence\t\t\tnew log likelihood\n")
            for i in range(0,len(ll_new_list)):
                for j in range(0,n):
                    file.write(str(phi_list[i][j]) + "\t")
                file.write(str(ll_new_list[i]) + "\n")
            file.close()

        #write_to_file(phi_list,new_ll_list)

        return (ll_new, model_parameters, latent_variables)

    # predict the allele type, copy number, subclone prev and subclone cluster
    # based on the trained model.
    def predict(self):
        J = self.stripePool.stripeNum

        for j in range(0, J):
            h_j, c_H_j, phi_j, subclone_cluster_j = self.predict_by_stripe(j)

            self.stripePool.stripes[j].genotype = h_j
            self.stripePool.stripes[j].copyNumber = c_H_j

            if h_j != constants.ALLELE_TYPE_BASELINE:
                self.stripePool.stripes[j].phi = phi_j
                self.stripePool.stripes[j].subclone_cluster = subclone_cluster_j


    def predict_by_stripe(self, j):
        h_j = 'NONE'
        c_H_j = -1
        phi_j = -1
        subclone_cluster_j = 'NONE'

        # 此处的处理方法不应该单独是
        # 如果杂合不缺失，使用RD+BAF
        # 如果杂合不缺失，只使用RD
        # Should be, check out that whether the target stripe locates above or
        # under baseline. If above, set copy number range [2, max_copy_number]
        # else set copy number range [0, 2]. If target stripe is baseline, set
        # copy number to be 2.

        loga = np.log(self.stripePool.stripes[j].tReadNum + 1) -\
            np.log(self.stripePool.stripes[j].nReadNum + 1)
        CNArray = np.array(self.config_parameters.allele_config_CN)
        indices = np.array([])

        if loga > self.stripePool.baseline:
            indices = np.where(CNArray > 2)[0]
        else:
            indices = np.where(CNArray <= 2)[0]

        if len(self.stripePool.stripes[j].pairedCounts) > 1:
            h_idx = self.latent_variables.sufficient_statistics[
                'psi'][j][indices].argmax()
            phi_idx = self.latent_variables.sufficient_statistics[
                'kappa'][j].argmax()
            h_j = np.array(self.config_parameters.allele_config)[indices][h_idx]
        else:
            ll_CNA_j = self.model_likelihood._ll_RD_by_stripe(self.model_parameters, j)
            phi_idx, h_idx = np.unravel_index(ll_CNA_j[:,indices].argmax(), ll_CNA_j[:,indices].shape)
            h_j = 'NONE'

        # 第一步需要从allele_config_CN中过滤出目标，然后在目标范围内进行求解最大
        # 值。
        # array

        c_H_j = np.array(self.config_parameters.allele_config_CN)[indices][h_idx]
        phi_j = self.model_parameters.parameters['phi'][phi_idx]
        subclone_cluster_j = phi_idx + 1

        return (h_j, c_H_j, phi_j, subclone_cluster_j)

    def _print_running_info(self, ll_new, ll_old, ll_change, phi_init, iters):
        phi_init_str = map("{0:.3f}".format, phi_init.tolist())
        phi_str = map("{0:.3f}".format, self.model_parameters.parameters['phi'].tolist())

        print "#" * 100
        print "# Running Info."
        print "#" * 100
        print "Model : joint"
        print "Maximum copy number : ", self.config_parameters.max_copynumber
        print "Subclone number : ", self.config_parameters.subclone_num
        print "Number of iterations : ", iters
        print "New log-likelihood : ", ll_new
        print "Old log-likelihood : ", ll_old
        print "Log-likelihood change : ", ll_change
        print "Initial subclone prevalence :  ", '\t'.join(phi_init_str)
        print "Estimated subclone prevalence :", '\t'.join(phi_str)
        sys.stdout.flush()

    def likelihood(self):
        J = self.stripePool.stripeNum
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num

        rho = self.model_parameters.parameters['rho']
        pi = self.model_parameters.parameters['pi']
        phi = self.model_parameters.parameters['phi']

        ll = 0

        for j in range(0, J):
            if len(self.stripePool.stripes[j].pairedCounts) < 1:
                continue

            ll_j = self.model_likelihood.ll_by_stripe(self.model_parameters, j)
            ll_j = np.log(rho[j].reshape((1, H))) + np.log(pi.reshape((K, 1))) + ll_j

            # for h in range(0, H):
                # h_T = self.config_parameters.allele_config[h]

                # 此处只是简单的去除三种情况。
                # 由于在ll_by_stripe中已经计算了BAF，如果出现杂合缺失的情况，自
                # 然会赋予对应的位置小概率值，所以此处应该不需要判断杂合缺失
                # if self.stripePool.segPool.segments[j].LOHStatus == 'FALSE' and check_balance_allele_type(h_T) == False:
                    # ll_j[:, h] = -1.0*constants.INF

                # if self.stripePool.segPool.segments[j].LOHStatus == 'TRUE' and check_balance_allele_type(h_T) == True:
                    # ll_j[:, h] = -1.0*constants.INF

                # if self.stripePool.segPool.segments[j].baselineLabel == 'TRUE' and h_T != constants.ALLELE_TYPE_BASELINE:
                    # ll_j[:, h] = -1.0*constants.INF

            ll_j = np.logaddexp.reduce(ll_j, axis=1)
            ll_j = np.logaddexp.reduce(ll_j, axis=0)

            ll += ll_j

        return ll

    def _E_step(self):
        J = self.stripePool.stripeNum
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num
        eta = constants.ETA

        rho = self.model_parameters.parameters['rho']
        pi = self.model_parameters.parameters['pi']
        phi = self.model_parameters.parameters['phi']

        for j in range(0, J):
            # if self.stripePool.segPool.segments[j].LOHStatus != 'NONE':
                # continue
            if len(self.stripePool.stripes[j].pairedCounts) < 1:
                continue

            ll_j = self.model_likelihood.ll_by_stripe(self.model_parameters, j)
            ll_j = np.log(rho[j].reshape((1, H))) + np.log(pi.reshape((K, 1))) + ll_j

            # 此处只是简单的去除三种情况。
            # 由于在ll_by_stripe中已经计算了BAF，如果出现杂合缺失的情况，自
            # 然会赋予对应的位置小概率值，所以此处应该不需要判断杂合缺失
            # for h in range(0, H):
                # h_T = self.config_parameters.allele_config[h]

                # if self.stripePool.segPool.segments[j].LOHStatus == 'FALSE' and check_balance_allele_type(h_T) == False:
                    # ll_j[:, h] = -1.0*constants.INF

                # if self.stripePool.segPool.segments[j].LOHStatus == 'TRUE' and check_balance_allele_type(h_T) == True:
                    # ll_j[:, h] = -1.0*constants.INF

                # if self.stripePool.segPool.segments[j].baselineLabel == 'TRUE' and h_T != constants.ALLELE_TYPE_BASELINE:
                    # ll_j[:, h] = -1.0*constants.INF

            psi_j_temp = np.logaddexp.reduce(ll_j, axis=0)
            kappa_j_temp = np.logaddexp.reduce(ll_j, axis=1)
            psi_j = log_space_normalise_rows_annealing(psi_j_temp.reshape((1, H)), eta)
            kappa_j = log_space_normalise_rows_annealing(kappa_j_temp.reshape((1, K)), eta)

            self.latent_variables.sufficient_statistics['psi'][j] = psi_j + constants.EPS
            self.latent_variables.sufficient_statistics['kappa'][j] = kappa_j + constants.EPS

    def _M_step(self):
        self._update_rho()

        self._update_pi()

        self._update_phi()

    def _update_rho(self):
        #x = constants.UPDATE_WEIGHTS['x']
        #y = constants.UPDATE_WEIGHTS['y']

        psi = np.array(self.latent_variables.sufficient_statistics['psi'])
        #omega = np.array(self.priors['omega'])

        rho_data = psi
        #rho_prior = omega/omega.sum()

        #rho = x*rho_data + y*rho_priors
        rho = rho_data

        self.model_parameters.parameters['rho'] =  rho

    def _update_pi(self):
        J = self.stripePool.stripeNum
        K = self.config_parameters.subclone_num
        kappa = np.array(self.latent_variables.sufficient_statistics['kappa'])

        J_ = 0
        kappa_ = np.zeros(K)

        for j in range(0, J):
            # if self.stripePool.segPool.segments[j].LOHStatus != 'NONE':
                # continue
            if len(self.stripePool.stripes[j].pairedCounts) < 1:
                continue

            kappa_ += kappa[j]
            J_ += 1

        pi = kappa_/J_

        self.model_parameters.parameters['pi'] = pi

    def _update_phi(self):
        K = self.config_parameters.subclone_num

        for k in range(0, K):
            self.model_parameters.parameters['phi'][k] = self._bisec_search_ll(k)

    def _bisec_search_ll(self, k):
        phi_start = 0.01
        phi_end = 0.99
        phi_stop = 1e-4
        phi_change = 1

        while phi_change > phi_stop:
            phi_left = phi_start + (phi_end - phi_start)*1/10
            phi_right = phi_start + (phi_end - phi_start)*9/10

            self.model_parameters.parameters['phi'][k] = phi_left
            ll_left = self.model_likelihood.complete_ll_by_subclone(self.model_parameters, self.latent_variables, k)
            self.model_parameters.parameters['phi'][k] = phi_right
            ll_right = self.model_likelihood.complete_ll_by_subclone(self.model_parameters, self.latent_variables, k)

            if ll_left >= ll_right:
                phi_change = phi_end - phi_right
                phi_end = phi_right
            else:
                phi_change = phi_left - phi_start
                phi_start = phi_left

        phi_optimum = (phi_start + phi_end)/2

        return phi_optimum


class JointConfigParameters(ConfigParameters):
    def __init__(self, max_copynumber, subclone_num):
        ConfigParameters.__init__(self, max_copynumber, subclone_num)

    def _init_components(self):
        self.copynumber = get_copynumber(self.max_copynumber)
        self.copynumber_num = get_copynumber_num(self.max_copynumber)
        self.genotype = get_genotype(self.max_copynumber)
        self.genotype_num = get_genotype_num(self.max_copynumber)
        self.allele_config = get_allele_config(self.max_copynumber)
        self.allele_config_num = get_allele_config_num(self.max_copynumber)
        self.allele_config_CN = get_allele_config_CN(self.max_copynumber)
        self.MU_G = get_MU_G(self.max_copynumber)
        self.Q_HG = get_Q_HG(self.max_copynumber)


class JointModelParameters(ModelParameters):
    def __init__(self, priors, stripePool, config_parameters):
        ModelParameters.__init__(self, priors, stripePool, config_parameters)

    def _init_parameters(self):
        J = self.stripePool.stripeNum
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num

        parameters = {}
        parameters['rho'] = np.ones((J, H))*1.0/H
        parameters['pi'] = np.ones(K)*1.0/K
        parameters['phi'] = np.random.random(K)

        self.parameters = parameters

    def reinit_parameters(self, phi):
        J = self.stripePool.stripeNum
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num

        parameters = {}
        parameters['rho'] = np.ones((J, H))*1.0/H
        parameters['pi'] = np.ones(K)*1.0/K
        parameters['phi'] = np.array(phi)

        self.parameters = parameters

    def copy_parameters(self, model_parameters):
        self.parameters['rho'] = np.array(model_parameters.parameters['rho'])
        self.parameters['pi'] = np.array(model_parameters.parameters['pi'])
        self.parameters['phi'] = np.array(model_parameters.parameters['phi'])


class JointLatentVariables(LatentVariables):
    def __init__(self, stripePool, config_parameters):
        LatentVariables.__init__(self, stripePool, config_parameters)

        self._init_components()

    def _init_components(self):
        J = self.stripePool.stripeNum
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num

        sufficient_statistics = {}
        sufficient_statistics['psi'] = np.zeros((J, H))
        sufficient_statistics['kappa'] = np.zeros((J, K))

        for j in range(0, J):
            sufficient_statistics['psi'][j] = rand_probs(H)
            sufficient_statistics['kappa'][j] = rand_probs(K)

        self.sufficient_statistics = sufficient_statistics

    def copy_latent_variables(self, latent_variables):
        self.sufficient_statistics['psi'] = np.array(latent_variables.sufficient_statistics['psi'])
        self.sufficient_statistics['kappa'] = np.array(latent_variables.sufficient_statistics['kappa'])


class JointModelLikelihood(ModelLikelihood):
    def __init__(self, priors, stripePool, config_parameters):
        ModelLikelihood.__init__(self, priors, stripePool, config_parameters)

    def ll_by_stripe(self, model_parameters, j):
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num

        ll = np.zeros((K, H))

        ll += self._ll_RD_by_stripe(model_parameters, j)
        ll += self._ll_BAF_by_stripe(model_parameters, j)

        return ll

    def _ll_RD_by_stripe(self, model_parameters, j):
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num

        phi = np.array(model_parameters.parameters['phi'])

        c_N = constants.COPY_NUMBER_NORMAL
        c_S = constants.COPY_NUMBER_BASELINE
        c_H = np.array(self.config_parameters.allele_config_CN)

        D_N_j = self.stripePool.stripes[j].nReadNum
        D_T_j = self.stripePool.stripes[j].tReadNum

        Lambda_S = self.stripePool.segPool.Lambda_S

        c_E_j = get_c_E(c_N, c_H, phi)
        lambda_E_j = D_N_j*c_E_j*Lambda_S/c_S

        ll_CNA_j = log_poisson_likelihood(D_T_j, lambda_E_j)

        return ll_CNA_j

    def _ll_BAF_by_stripe(self, model_parameters, j):
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num
        G = self.config_parameters.genotype_num
        Q_HG = np.array(self.config_parameters.Q_HG).reshape(1, 1, H, G)

        phi = np.array(model_parameters.parameters['phi'])

        c_N = constants.COPY_NUMBER_NORMAL
        c_H = np.array(self.config_parameters.allele_config_CN)
        mu_N = constants.MU_N
        mu_G = np.array(self.config_parameters.MU_G)
        mu_E = get_mu_E_joint(mu_N, mu_G, c_N, c_H, phi)

        a_T_j = self.stripePool.stripes[j].pairedCounts[:, 2]
        b_T_j = self.stripePool.stripes[j].pairedCounts[:, 3]

        d_T_j = a_T_j + b_T_j

        ll = np.log(Q_HG) + log_binomial_likelihood_joint(b_T_j, d_T_j, mu_E)
        ll_BAF_j = np.logaddexp.reduce(ll, axis=3).sum(axis=0)

        return ll_BAF_j

    def complete_ll_by_subclone(self, model_parameters, latent_variables, k):
        J = self.stripePool.stripeNum
        H = self.config_parameters.allele_config_num

        rho = np.array(model_parameters.parameters['rho'])
        pi = np.array(model_parameters.parameters['pi'])
        phi = np.array(model_parameters.parameters['phi'])
        psi = np.array(latent_variables.sufficient_statistics['psi'])
        kappa = np.array(latent_variables.sufficient_statistics['kappa'])

        ll = 0

        for j in range(0, J):
            # 此处是防止杂合位点过少而无法精准判断
            # 由于我们计算的是条带所以此处判断条带的pairedcounts，如果没有
            # 继续
            if len(self.stripePool.stripes[j].pairedCounts) < 1:
                continue

            ll_j = self.complete_ll_by_subclone_seg(model_parameters, k, j)
            ll_j = np.log(rho[j].reshape((1, H))) + np.log(pi[k]) + ll_j
            ll_j = kappa[j, k]*psi[j].reshape((1, H))*ll_j

            ll += ll_j.sum()

        return ll

    def complete_ll_by_subclone_seg(self, model_parameters, k, j):
        H = self.config_parameters.allele_config_num

        phi = np.array(model_parameters.parameters['phi'])

        ll = np.zeros((1, H))

        ll += self._ll_RD_by_subclone_seg(phi[k], j)
        #ll += self._ll_LOH_by_subclone_seg(phi[k], j)
        #CNA data is effectively enough to estimate phi, and LOH computation is slow

        return ll

    def _ll_RD_by_subclone_seg(self, phi, j):
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num

        c_N = constants.COPY_NUMBER_NORMAL
        c_S = constants.COPY_NUMBER_BASELINE
        c_H = np.array(self.config_parameters.allele_config_CN)

        D_N_j = self.stripePool.stripes[j].nReadNum
        D_T_j = self.stripePool.stripes[j].tReadNum

        Lambda_S = self.stripePool.segPool.Lambda_S

        c_E_j = get_c_E(c_N, c_H, phi)
        lambda_E_j = D_N_j*c_E_j*Lambda_S/c_S

        ll_CNA_j = log_poisson_likelihood(D_T_j, lambda_E_j)

        return ll_CNA_j

    def _ll_BAF_by_subclone_seg(self, phi, j):
        H = self.config_parameters.allele_config_num
        K = self.config_parameters.subclone_num
        G = self.config_parameters.genotype_num
        Q_HG = np.array(self.config_parameters.Q_HG).reshape(1, 1, H, G)

        c_N = constants.COPY_NUMBER_NORMAL
        c_H = np.array(self.config_parameters.allele_config_CN)
        mu_N = constants.MU_N
        mu_G = np.array(self.config_parameters.MU_G)
        mu_E = get_mu_E_joint(mu_N, mu_G, c_N, c_H, phi)

        a_T_j = self.stripePool.stripes[j].pairedCounts[:, 2]
        b_T_j = self.stripePool.stripes[j].pairedCounts[:, 3]

        d_T_j = a_T_j + b_T_j

        ll = np.log(Q_HG) + log_binomial_likelihood_joint(b_T_j, d_T_j, mu_E)
        ll_BAF_j = np.logaddexp.reduce(ll, axis=3).sum(axis=0)

        return ll_BAF_j


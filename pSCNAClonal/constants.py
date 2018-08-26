'''
# =============================================================================
#      FileName: constants.py
#          Desc: constants/parameters for preprocess
#        Author: Chu Yanshuo
#         Email: chu@yanshuo.name
#      HomePage: http://yanshuo.name
#       Version: 0.0.1
#    LastChange: 2018-03-03 08:52:28
#       History:
# =============================================================================
'''

import numpy as np


###################
#  RD parameters  #
###################

MINIMUM_POSITIVE=0.0000001




###########################
#  MCMC model parameters  #
###########################

ZOOM_P = 5
X_ZOOM_IN_FACTOR = 10

DOWN_GC_BOUNDARY_PERCENTILE = 30
UP_GC_BOUNDARY_PERCENTILE = 70
DOWN_LOGA_BOUNDARY_PERCENTILE = 30
UP_LOGA_BOUNDARY_PERCENTILE = 70
SLOPE_RANGE = 5


##############
#  COVERAGE  #
##############

COVERAGE = 30

####################
#  BAF parameters  #
####################
BAF_THRESHOLD = 0.35
BAF_N_MIN = 0.35

BAF_COUNTS_MIN = 10
BAF_COUNTS_MAX = 95

BAF_BINS = np.array(range(0, 100 + 1))/100.0
LOH_FRAC_MAX = 0.25
SITES_NUM_MIN = 5
BINOM_TEST_P = 0.5
# default BINOM_TEST_THRED = 0.025
# for 30x read depth,
BINOM_TEST_THRED = 0.025
BINOM_TEST_THRED_APM = 0.18

APM_N_MIN = 0.40 #This parameter is very important for baseline selection

EMPIRI_BAF = 0.485
EMPIRI_AAF = 1.0 - EMPIRI_BAF
MU_N = EMPIRI_BAF/(EMPIRI_BAF + EMPIRI_AAF)

########################################
#  Hierarchical clustering parameters  #
########################################

# HCC1954  n5t95 ~ n60t40
HC_THRESH = 0.005
# HCC1954  n80t20
#HC_THRESH = 0.001
# HCC1954  n95t5
#HC_THRESH = 0.0001


########################
#  Copy number config  #
########################

COPY_NUMBER_NORMAL = 2


######################
#  Chrom parameters  #
######################

CHROM_START = 0

CHROM_IDX_LIST = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19,
              20, 21, 22]


################################
#  Model structure parameters  #
################################


RD_WEIGHT = 0.5
RD_WEIGHT_TSSB = 0.5

VARPI = 0.8 ## gap parameters

#############################
#  Stripe range parameters  #
#############################

YDOWN = -5
# YDOWN = -1.2
YUP = 5
# YUP = 1.37
STRIPENUM = 6
#STRIPENUM = 3
NOISESTRIPENUM = 0


#############################
# Constants from model      #
#############################

BAF_N_MIN = 0.4
BAF_N_MAX = 0.6

PHI_INIT = [0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]
PHI_RANGE = [i/100.0 for i in range(2, 99)]

BURN_IN = 10
EPS = np.finfo(float).eps
ETA = 1.0
INF = float('inf')
LL_RATIO_CHANGE_THRED = 0.01
LL_PERCENT_CHANGE_THRED = 0.90

TAU = 500
SIGMA = 0.0001
ERR = 0.01

COPY_NUMBER_BASELINE = 2
ALLELE_TYPE_BASELINE = 'PM'

UPDATE_WEIGHTS = {}
UPDATE_WEIGHTS['x'] = 0.9
UPDATE_WEIGHTS['y'] = 0.1

################################
# Stripe decompose parameters  #
################################

DECOMPOSE_NUMBER_THRESHOLD = 10

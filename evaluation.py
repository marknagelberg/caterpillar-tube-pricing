import math
import numpy as np
from sklearn.cross_validation import KFold

'''
Calculates Root Mean Squared Logarithmic Error (RMSLE) - the error metric 
#upon which models in the competition were evaluated
'''
def rmsle(y, y_pred):
	assert len(y) == len(y_pred)
	terms_to_sum = [(math.log(y_pred[i] + 1) - math.log(y[i] + 1)) ** 2.0 for i,pred in enumerate(y_pred)]
	return (sum(terms_to_sum) * (1.0/len(y))) ** 0.5

'''
Calculates k-fold CV scores for an sklearn classifier clf, using
the feature names specified in the feature_names array that should appear 
in training data X.
'''
def get_kfold_scores(X, y, n_folds, clf, feature_names, random_state  = 10):
    score_total = 0.0
    kf = KFold(len(X), n_folds=n_folds, random_state = random_state)

    for train_index, test_index in kf:
    	X_train = X.loc[train_index]
    	y_train = y.loc[train_index]
    	clf.fit(X_train[feature_names], y_train)
    	X_test = X.loc[test_index]
    	y_test = y.loc[test_index]
    	predictions = clf.predict(X_test[feature_names])
        predictions = np.exp(predictions) - 1
        y_test = np.exp(y_test) - 1
    	score = rmsle(y = y_test.tolist(), y_pred = predictions)
    	score_total += score
    	print "Score: " + str(score)
    
    average_score = score_total/float(n_folds)
    print "Average score: " + str(average_score)


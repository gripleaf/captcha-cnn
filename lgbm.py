#coding: utf-8
#!/usr/bin/python
import numpy as np
import pandas as pd
import lightgbm as lgb
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split, GridSearchCV
from PIL import Image, ImageFilter, ImageEnhance
from split import get_word_imgs

# specify your configurations as a dict
params = {
    'task': 'train',
    'boosting_type': 'gbdt',
    'objective': 'multiclass',
    'num_class': 36,
    'metric': 'multi_logloss',
    # 'max_bin': 255,
    'max_depth': 10,
    'learning_rate': 0.25,
    'num_leaves': 200,
    'verbose': 1,
    #'feature_fraction': 0.8
}


def train_model(model_file='ckpt/lgb'):
    print "load data ..."
    dataset = pd.read_csv("train.csv", header=0)
    dataset2 = pd.read_csv("data.csv", header=0)
    train_X = dataset.iloc[:, 1:].values
    train_Y = dataset.iloc[:, 0].values
    test_X = dataset2.iloc[:, 1:].values
    test_Y = dataset2.iloc[:, 0].values
    #train_X, test_X, train_Y, test_Y = train_test_split(
    #    d_x, d_y, test_size=0.33, random_state=42)

    lgb_train = lgb.Dataset(train_X, label=train_Y)
    lgb_eval = lgb.Dataset(test_X, label=test_Y, reference=lgb_train)

    print "begin train..."
    bst = lgb.train(
        params,
        lgb_train,
        valid_sets=[lgb_eval],
        num_boost_round=100,
        #early_stopping_rounds=10)
    )
    print "train end\nsaving..."
    bst.save_model(model_file)
    return bst


def tune_model(data_file="train.csv"):
    print "load data ..."
    dataset = pd.read_csv(data_file, header=0)
    d_x = dataset.iloc[:, 1:].values
    d_y = dataset.iloc[:, 0].values

    print "create classifier..."
    param_grid = {
        "reg_alpha": [0.1],
        "learning_rate": [0.22, 0.25],
        'num_leaves': [200],
        'max_depth': [8, 9, 10]
    }
    params = {
        'objective': 'multiclass',
        'metric': 'multi_logloss',
        'max_bin': 255,
        'max_depth': 7,
        'learning_rate': 0.25,
        'num_leaves': 80,
    }
    # max_depth = 7, learning_rate:0.25
    model = lgb.LGBMClassifier(
        boosting_type='gbdt',
        objective="multiclass",
        n_jobs=8,
        random_state=42)
    model.n_classes = 36
    print "run grid search..."
    searcher = GridSearchCV(estimator=model, param_grid=param_grid, cv=3)
    searcher.fit(d_x, d_y)
    print searcher.grid_scores_
    print "=" * 30, '\n'
    print searcher.best_params_
    print "=" * 30, '\n'
    print searcher.best_score_
    print "end"


def predict_code(filepath):
    Image.open(filepath).show()
    bst = lgb.Booster(params={'num_threads': 1}, model_file="ckpt/lgb")
    ims = get_word_imgs(filepath)

    pred = bst.predict(np.array(ims))
    pred = map(lambda x: sum([i * round(y) for i, y in enumerate(x)]), pred)
    # print pred
    print [
        chr(int(x) + ord('0'))
        if x >= 0 and x <= 9 else chr(int(x) + ord('A')) for x in pred
    ]


if __name__ == "__main__":
    # 训练模型，并保存模型
    train_model('ckpt/lgb')
    # 调参
    # tune_model()
    # 预测数据，需要先训练模型得到保存的模型
    # predict_code('login_code.jpg')

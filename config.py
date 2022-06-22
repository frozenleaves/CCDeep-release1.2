#! /usr/bin/python3
# -*- coding: utf-8 -*-
# @FileName: config.py
# @Author: Li Chengxin 
# @Time: 2022/4/18 15:44


from __future__ import annotations
import os


TIMES = 20  # Image magnification

# some training parameters
EPOCHS = 100
BATCH_SIZE = 128
NUM_CLASSES = 3  # cell phase num
image_height = 100
image_width = 100
LEARNING_RATE = 1e-6
channels = 2  # image channels

train_process_20x_detail_data_savefile = './train_detail_20x_dev1.3.4.csv'
train_process_60x_detail_data_savefile = '/home/zje/CellClassify/train_detail_60x.csv'

save_model_dir_60x = '/home/zje/CellClassify/saved_models/saved_60x_classify_model/model'
dataset_dir_mcy_60x = '/home/zje/CellClassify/train_dataset/train_data_60x_new/train_mcy'
train_dir_mcy_60x = os.path.join(dataset_dir_mcy_60x, "train")
valid_dir_mcy_60x = os.path.join(dataset_dir_mcy_60x, "valid")
test_dir_mcy_60x = os.path.join(dataset_dir_mcy_60x, "test")

dataset_dir_dic_60x = '/home/zje/CellClassify/train_dataset/train_data_60x_new/train_dic'
train_dir_dic_60x = os.path.join(dataset_dir_dic_60x, "train")
valid_dir_dic_60x = os.path.join(dataset_dir_dic_60x, "valid")
test_dir_dic_60x = os.path.join(dataset_dir_dic_60x, "test")

save_model_dir_20x = './saved_classify_models/saved_20x_classify_model_dev1.3.4/model'
save_model_dir_20x_best = './saved_classify_models/saved_20x_classify_model_dev1.3.4_best/model'
dataset_dir_mcy_20x = '/home/zje/CellClassify/train_dataset/train_data_20x_dev1.3.4/train_mcy'
train_dir_mcy_20x = os.path.join(dataset_dir_mcy_20x, "train")
valid_dir_mcy_20x = os.path.join(dataset_dir_mcy_20x, "valid")
test_dir_mcy_20x = os.path.join(dataset_dir_mcy_20x, "test")

dataset_dir_dic_20x = '/home/zje/CellClassify/train_dataset/train_data_20x_dev1.3.4/train_dic'
train_dir_dic_20x = os.path.join(dataset_dir_dic_20x, "train")
valid_dir_dic_20x = os.path.join(dataset_dir_dic_20x, "valid")
test_dir_dic_20x = os.path.join(dataset_dir_dic_20x, "test")

# segmentation model config

# 60x
model_name = 'segment_60x_model'
model_saved_dir = '/home/zje/CellClassify/saved_models/saved_60x_segment_model/'
tain_dataset = '/home/zje/CellClassify/train_dataset/segment_train_60x/train/images'
train_label = '/home/zje/CellClassify/train_dataset/segment_train_60x/train/masks'
valid_size = 0.1

# 20x
model_name_20x = 'segment_20x_model'
model_saved_dir_20x = './saved_segment_models/saved_20x_segment_model_1.3.4/'
train_dataset_20x = '/home/zje/CellClassify/train_dataset/segment_train_20x/train/images'
train_label_20x = '/home/zje/CellClassify/train_dataset/segment_train_20x/train/masks'

valid_size_20x = 0.1

# choose a network
# model = "resnet18"
# model = "resnet34"
model = "resnet50"
# model = "resnet101"
# model = "resnet152"

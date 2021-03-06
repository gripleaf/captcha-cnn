#coding:utf-8
import numpy as np
import tensorflow as tf
from gen_captcha import batch_gen_captcha_text_and_image
import random
from gen_captcha import number
from gen_captcha import ALPHABET
from PIL import Image, ImageFilter, ImageEnhance
import os
import tensorflow.contrib.slim as slim
# 图像大小
IMAGE_HEIGHT = 40
IMAGE_WIDTH = 150
MAX_CAPTCHA = 4

#print("验证码文本最长字符数", MAX_CAPTCHA)  # 验证码最长4字符; 我全部固定为4,可以不固定. 如果验证码长度小于4，用'_'补齐


# 把彩色图像转为灰度图像（色彩对识别验证码没有什么用）
def convert2gray(img):
    img = img.filter(ImageFilter.MedianFilter())
    img = ImageEnhance.Sharpness(img.convert("L")).enhance(2)
    return [1 if x > 140 else 0 for x in np.array(img).flatten()]


"""
cnn在图像大小是2的倍数时性能最高, 如果你用的图像大小不是2的倍数，可以在图像边缘补无用像素。
np.pad(image【,((2,3),(2,2)), 'constant', constant_values=(255,))  # 在图像上补2行，下补3行，左补2行，右补2行
"""

# 文本转向量
CHAR_SET_LEN = len(number + ALPHABET)


def text2vec(text):
    text_len = len(text)
    if text_len != MAX_CAPTCHA:
        raise ValueError('验证码最长4个字符' + text)

    vector = np.zeros(MAX_CAPTCHA * CHAR_SET_LEN)

    def char2pos(c):
        k = ord(c) - ord('0')
        if k > 9:
            k = ord(c) - ord('A') + 10
            if k >= 36:
                raise ValueError('No Map')
        return k

    for i, c in enumerate(text):
        idx = i * CHAR_SET_LEN + char2pos(c)
        vector[idx] = 1
    return vector


# 向量转回文本
def vec2text(vec):
    char_pos = vec.nonzero()[0]
    text = []
    for i, c in enumerate(char_pos):
        char_idx = c % CHAR_SET_LEN
        if char_idx < 10:
            char_code = char_idx + ord('0')
        elif char_idx < 36:
            char_code = char_idx - 10 + ord('A')
        else:
            raise ValueError('error')
        text.append(chr(char_code))
    return "".join(text)


"""
#向量（大小MAX_CAPTCHA*CHAR_SET_LEN）用0,1编码 每63个编码一个字符，这样顺利有，字符也有
vec = text2vec("F5Sd")
text = vec2text(vec)
print(text)  # F5Sd
vec = text2vec("SFd5")
text = vec2text(vec)
print(text)  # SFd5
"""


# 生成一个训练batch
def get_next_batch(batch_size=256):
    batch_x = np.zeros([batch_size, IMAGE_HEIGHT * IMAGE_WIDTH])
    batch_y = np.zeros([batch_size, MAX_CAPTCHA * CHAR_SET_LEN])

    ims = batch_gen_captcha_text_and_image(batch_size)

    for i in range(batch_size):
        text, image = ims[i]
        image = convert2gray(image)
        # print image.shape
        batch_x[
            i, :] = image  #.flatten() / 255  # (image.flatten()-128)/128  mean为0
        batch_y[i, :] = text2vec(text)
        # print text
        # print text2vec(text), vec2text(text2vec(text))
    # print batch_x.shape, batch_y.shape
    return batch_x, batch_y


####################################################################

X = tf.placeholder(tf.float32, [None, IMAGE_HEIGHT * IMAGE_WIDTH])
Y = tf.placeholder(tf.float32, [None, MAX_CAPTCHA * CHAR_SET_LEN])
keep_prob = tf.placeholder(tf.float32)  # dropout


# 定义CNN
def crack_captcha_cnn(w_alpha=0.01, b_alpha=0.1):
    x = tf.reshape(X, shape=[-1, IMAGE_HEIGHT, IMAGE_WIDTH, 1])

    #w_c1_alpha = np.sqrt(2.0/(IMAGE_HEIGHT*IMAGE_WIDTH)) #
    #w_c2_alpha = np.sqrt(2.0/(3*3*32))
    #w_c3_alpha = np.sqrt(2.0/(3*3*64))
    #w_d1_alpha = np.sqrt(2.0/(8*32*64))
    #out_alpha = np.sqrt(2.0/1024)

    # 3 conv layer
    w_c1 = tf.Variable(w_alpha * tf.random_normal([3, 3, 1, 32]))
    b_c1 = tf.Variable(b_alpha * tf.random_normal([32]))
    conv1 = tf.nn.relu(
        tf.nn.bias_add(
            tf.nn.conv2d(x, w_c1, strides=[1, 1, 1, 1], padding='SAME'), b_c1))
    conv1 = tf.nn.max_pool(
        conv1, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
    conv1 = tf.nn.dropout(conv1, keep_prob)

    w_c2 = tf.Variable(w_alpha * tf.random_normal([3, 3, 32, 64]))
    b_c2 = tf.Variable(b_alpha * tf.random_normal([64]))
    conv2 = tf.nn.relu(
        tf.nn.bias_add(
            tf.nn.conv2d(conv1, w_c2, strides=[1, 1, 1, 1], padding='SAME'),
            b_c2))
    conv2 = tf.nn.max_pool(
        conv2, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
    conv2 = tf.nn.dropout(conv2, keep_prob)

    w_c3 = tf.Variable(w_alpha * tf.random_normal([3, 3, 64, 64]))
    b_c3 = tf.Variable(b_alpha * tf.random_normal([64]))
    conv3 = tf.nn.relu(
        tf.nn.bias_add(
            tf.nn.conv2d(conv2, w_c3, strides=[1, 1, 1, 1], padding='SAME'),
            b_c3))
    conv3 = tf.nn.max_pool(
        conv3, ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1], padding='SAME')
    conv3 = tf.nn.dropout(conv3, keep_prob)

    # batch normalize
    batch_mean, batch_var = tf.nn.moments(
        conv3, range(len(conv3.shape) - 1), keep_dims=True)
    shift = tf.Variable(
        tf.constant(0.0, shape=[conv3.shape[-1]], name='shift'))
    scale = tf.Variable(
        tf.constant(1.0, shape=[conv3.shape[-1]], name='scale'))
    epsilon = 1e-3
    bno2 = tf.nn.batch_normalization(conv3, batch_mean, batch_var, shift,
                                     scale, epsilon)

    # Fully connected layer
    # print bno2.shape
    w_d = tf.Variable(w_alpha * tf.random_normal([5 * 19 * 64, 1024]))
    b_d = tf.Variable(b_alpha * tf.random_normal([1024]))
    dense = tf.reshape(bno2, [-1, w_d.get_shape().as_list()[0]])
    dense = tf.nn.relu(tf.add(tf.matmul(dense, w_d), b_d))
    dense = tf.nn.dropout(dense, keep_prob)

    dense = slim.fully_connected(dense, 2048, activation_fn=None, scope="fc2")
    dense = slim.fully_connected(dense, 2024, activation_fn=None, scope="fc5")
    dense = slim.fully_connected(dense, 1024, activation_fn=None, scope="fc6")

    w_out = tf.Variable(
        w_alpha * tf.random_normal([1024, MAX_CAPTCHA * CHAR_SET_LEN]))
    b_out = tf.Variable(
        b_alpha * tf.random_normal([MAX_CAPTCHA * CHAR_SET_LEN]))
    out = tf.add(tf.matmul(dense, w_out), b_out)
    #out = tf.nn.softmax(out)
    return out


# 训练
def train_crack_captcha_cnn():
    output = crack_captcha_cnn()
    # loss
    #loss = tf.reduce_mean(tf.nn.softmax_cross_entropy_with_logits(output, Y))
    loss = tf.reduce_mean(
        tf.nn.sigmoid_cross_entropy_with_logits(logits=output, labels=Y))
    # 最后一层用来分类的softmax和sigmoid有什么不同？
    # optimizer 为了加快训练 learning_rate应该开始大，然后慢慢衰
    optimizer = tf.train.AdamOptimizer().minimize(loss)

    predict = tf.reshape(output, [-1, MAX_CAPTCHA, CHAR_SET_LEN])
    max_idx_p = tf.argmax(predict, 2)
    max_idx_l = tf.argmax(tf.reshape(Y, [-1, MAX_CAPTCHA, CHAR_SET_LEN]), 2)
    correct_pred = tf.equal(max_idx_p, max_idx_l)
    accuracy = tf.reduce_mean(tf.cast(correct_pred, tf.float32))

    saver = tf.train.Saver()

    with tf.Session() as sess:
        step = 1
        sess.run(tf.global_variables_initializer())
        if os.path.exists("ckpt"):
            ckpt = tf.train.get_checkpoint_state("ckpt")
            if ckpt and ckpt.model_checkpoint_path:
                saver.restore(sess, ckpt.model_checkpoint_path)

        while True:
            batch_x, batch_y = get_next_batch(128)
            _, loss_ = sess.run(
                [optimizer, loss],
                feed_dict={X: batch_x,
                           Y: batch_y,
                           keep_prob: 1})
            #print(step, loss_)

            # 每100 step计算一次准确率
            if step % 100 == 0:
                batch_x_test, batch_y_test = get_next_batch(100)
                acc = sess.run(
                    accuracy,
                    feed_dict={
                        X: batch_x_test,
                        Y: batch_y_test,
                        keep_prob: 1.
                    })
                print(step, acc)
                # 如果准确率大于50%,保存模型,完成训练
                if acc > 0.999:
                    saver.save(
                        sess,
                        "ckpt/crack_capcha.model" + str(step),
                        global_step=step)
                    break
            if step % 200 == 0:
                saver.save(
                    sess,
                    "ckpt/crack_capcha.model" + str(step),
                    global_step=step)
            step += 1


def crack_captcha(captcha_image):
    output = crack_captcha_cnn()

    saver = tf.train.Saver()
    with tf.Session() as sess:
        saver.restore(sess, tf.train.latest_checkpoint('ckpt'))

        predict = tf.argmax(
            tf.reshape(output, [-1, MAX_CAPTCHA, CHAR_SET_LEN]), 2)
        text_list = sess.run(
            predict, feed_dict={X: [captcha_image],
                                keep_prob: 1})

        text = text_list[0].tolist()
        vector = np.zeros(MAX_CAPTCHA * CHAR_SET_LEN)
        i = 0
        for n in text:
            vector[i * CHAR_SET_LEN + n] = 1
            i += 1
        return vec2text(vector)


def get_session():
    output = crack_captcha_cnn()

    saver = tf.train.Saver()
    sess = tf.Session()
    saver.restore(sess, tf.train.latest_checkpoint('ckpt'))
    predict = tf.argmax(tf.reshape(output, [-1, MAX_CAPTCHA, CHAR_SET_LEN]), 2)

    return sess, predict


def sess_predict_code(sess, predict, filepath):
    image = Image.open(filepath)
    # image.show()
    image = convert2gray(image)
    text_list = sess.run(predict, feed_dict={X: [image], keep_prob: 1})

    text = text_list[0].tolist()
    vector = np.zeros(MAX_CAPTCHA * CHAR_SET_LEN)
    i = 0
    for n in text:
        vector[i * CHAR_SET_LEN + n] = 1
        i += 1
    predict_text = vec2text(vector)
    print("预测: {}".format(predict_text))
    return predict_text


def predict_code(filepath):
    image = Image.open(filepath)
    # image.show()
    image = convert2gray(image)
    predict_text = crack_captcha(image)
    print("预测: {}".format(predict_text))
    return predict_text


if __name__ == '__main__':
    # image = Image.open("login_code.jpg")
    # image = np.array(image)
    # image = convert2gray(image)
    # image = image.flatten() / 255
    # predict_text = crack_captcha(image)
    # print("正确: {}  预测: {}".format(text, predict_text))
    train_crack_captcha_cnn()
    # predict_code("login_code.jpg")

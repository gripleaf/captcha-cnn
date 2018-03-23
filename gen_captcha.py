# coding:utf-8
import numpy as np
from PIL import Image
import random
import time
import os
# 验证码中的字符, 就不用汉字了
number = ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9']
ALPHABET = [
    'A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O',
    'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'
]


# 验证码一般都无视大小写；验证码长度4个字符
def random_captcha_text(char_set=number + ALPHABET, captcha_size=4):
    captcha_text = []
    for i in range(captcha_size):
        c = random.choice(char_set)
        captcha_text.append(c)
    return captcha_text


def batch_gen_captcha_text_and_image(size=100):
    pt = './train'
    imgs = random.sample(os.listdir(pt), size)
    ims = []
    for img in imgs:
        c_img = Image.open(os.path.join(pt, img))
        # c_img = np.array(c_img)
        #print img[:-4]
        ims.append((img[:-4], c_img))
    # imgs = random.sample(os.listdir("./data"), 10)
    # for img in imgs:
    #     c_img = Image.open(os.path.join('./data', img))
    #     ims.append((img[:-4], c_img))
    #os.system("rm " + " ".join([os.path.join(pt, img) for img in imgs]))
    return ims


if __name__ == '__main__':
    # 测试
    for i in range(5000):
        print(i)
        # print 'begin ', time.ctime(), type(image)
        # f = plt.figure()
        # ax = f.add_subplot(111)
        # ax.text(
        #     0.1, 0.9, text, ha='center', va='center', transform=ax.transAxes)
        # plt.imshow(image)
        # plt.show()
        # print 'end ', time.ctime()

# Few_Shot_Image_Classification 
Many of the deep learning algorithms which achieved great success in solving supervised learning problems, rely on huge labeled data. The approach of training such models
require large amount of labelled data in order to perform well, due to this such models are not suited for tasks with less labelled data. This motivates us to look into few-shot
learning, which aims to learn quickly from a few data samples. Meta learning was proposed as a framework to solve
tasks in few-shot learning settings. The basic idea behind
meta learning is to train a model with a variety of tasks,
such that the learned model can perform well on new tasks
only with few data samples. Model Agnostic Meta Learning (MAML) is a representative meta learning algorithm
which can be applied to any Neural Network architecture.
In MAML a meta learner learns a good initialization of parameters such that the base learner can adapt to any new
task with just a few examples. we attempt to improve the
accuracy of MAML by incorporating in which additional
data is generated by a Generative network. We claim this
method due to availability of more data can learn better decision boundaries, which leads to better performance. We
have compared the performance of MAML model and with
our GAN based model. We have evaluated our model on
image recognition problems, for 1 shot and 5 shot learning
setting on Omniglot and Mini Imagenet datasets. Our results show that our proposed model outperforms standard
MAML in terms of training accuracy
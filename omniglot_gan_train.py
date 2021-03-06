import matplotlib
matplotlib.use('Agg')
import  torch, os
import  numpy as np
from    omniglotNShot import OmniglotNShot
import  argparse
from    meta_gan import MetaGAN
from matplotlib import pyplot as plt
from PIL import Image
import json
from datetime import datetime

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        print("you probably tried to make a new model in the same minute, wait a couple seconds")
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def save_train_accs(path, accs, epoch):
    file = open(path +  '/q_nway_train_accuracies.txt', 'ab')
    np.savetxt(file, [np.insert(accs["q_nway"],0, epoch)])
    file.close()

    file = open(path +  '/q_discrim_train_accuracies.txt', 'ab')
    np.savetxt(file, [np.insert(accs["q_discrim"],0, epoch)])
    file.close()

    file = open(path +  '/gen_nway_train_accuracies.txt', 'ab')
    np.savetxt(file, [np.insert(accs["gen_nway"],0, epoch)])
    file.close()

    file = open(path +  '/gen_discrim_train_accuracies.txt', 'ab')
    np.savetxt(file,  [np.insert(accs["gen_discrim"],0, epoch)])
    file.close()

def save_test_accs(path, accs, epoch):
    file = open(path +  '/q_nway_test_accuracies.txt', 'ab')

    print(np.insert(accs,0, epoch))
    np.savetxt(file, [np.insert(accs,0, epoch)])
    file.close()



def save_imgs(path, imgs, step):
    # save raw txt files
    img_f=open(path+"/images_step" + str(step) + ".txt",'ab')
    some_imgs = np.reshape(imgs, [imgs.shape[0]*imgs.shape[1], -1])[0:50]
    np.savetxt(img_f,some_imgs)
    img_f.close()

    os.environ['KMP_DUPLICATE_LIB_OK']='True'
    # save png of imgs
    i = 0
    for flat_img in some_imgs:
        img = flat_img.reshape(28,28)

        if i < 50:
            plt.subplot(5, 10, 1 + i)
            plt.axis('off')
            plt.imshow(img, cmap='Greys')
        i += 1
    plt.savefig(path+"/images_step" + str(step) + ".png")
    plt.close()

def main(args):

    torch.manual_seed(222)
    torch.cuda.manual_seed_all(222)
    np.random.seed(222)

    print(args)


    shared_config = [
        ('conv2d', [64, 1, 3, 3, 2, 0]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
        ('conv2d', [64, 64, 3, 3, 2, 0]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
    ]

    nway_config = [
        ('conv2d', [64, 1, 3, 3, 2, 0]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
        ('conv2d', [64, 64, 3, 3, 2, 0]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
        ('conv2d', [64, 64, 3, 3, 2, 0]),
        ('relu', [True]),
        ('bn', [64]),
        ('conv2d', [64, 64, 2, 2, 1, 0]),
        ('relu', [True]),
        ('bn', [64]),
        ('flatten', []),
        ('linear', [args.n_way, 64])
    ]

    # reads in image
    discriminator_config = [
        ('conv2d', [64, 1, 3, 3, 2, 0]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
        ('conv2d', [64, 64, 3, 3, 2, 0]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
        ('conv2d', [64, 64, 3, 3, 2, 0]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
        ('conv2d', [64, 64, 2, 2, 1, 0]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
        ('flatten', []),
        ('linear', [1, 64])
        # don't use a sigmoid at the end
    ]

    # new gen_config
    # starts from image and convolves it into new ones
    gen_config = [
        ('convt2d', [1, 64, 3, 3, 1, 1]),
        ('leakyrelu', [.2, True]),
        ('bn', [64]),
        ('random_proj', [100, 28, 64]),
        ('convt2d', [128, 64, 3, 3, 1, 1]),
        #('convt2d', [1, 128, 4, 4, 2, 1]), # [ch_in, ch_out, kernel_sz, kernel_sz, stride, padding]
        ('relu', [.2, True]),
        ('bn', [64]),
        # ('encode', [1024, 64*28*28]),
        # ('decode', [64*28*28, 1024]),
        ('relu', [.2, True]),
        ('conv2d', [64, 64, 3, 3, 1, 1]),
        #('convt2d', [1, 128, 4, 4, 2, 1]), # [ch_in, ch_out, kernel_sz, kernel_sz, stride, padding]
        ('relu', [.2, True]),
        ('bn', [64]),
        ('conv2d', [1, 64, 3, 3, 1, 1]),
        ('sigmoid', [True])
    ]


    # old gen_config
    # gen_config = [
    #     ('random_proj', [100, 512, 64, 7]), # [latent_dim, emb_size, ch_out, h_out/w_out]
    #     # img: (64, 7, 7)
    #     ('convt2d', [64, 32, 4, 4, 2, 1]), # [ch_in, ch_out, kernel_sz, kernel_sz, stride, padding]
    #     ('bn', [32]),
    #     ('relu', [True]),
    #     # img: (32, 14, 14)
    #     ('convt2d', [32, 1, 4, 4, 2, 1]),
    #     # img: (1, 28, 28)
    #     ('sigmoid', [True])
    # ]

    # if args.condition_discrim:
    #     discriminator_config = [
    #         ('condition', [512, 1, 6]), # [emb_dim, emb_ch_out, h_out/w_out]
    #         ('conv2d', [128, 65, 2, 2, 1, 0]),
    #         ('leakyrelu', [.2, True]),
    #         ('bn', [128]),
    #         ('conv2d', [128, 128, 2, 2, 1, 0]),
    #         ('leakyrelu', [.2, True]),
    #         ('bn', [128]),
    #         ('flatten', []),
    #         ('linear', [1, 2048])
    #     ]


    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    mamlGAN = MetaGAN(args, shared_config, nway_config, discriminator_config, gen_config).to(device)


    tmp = filter(lambda x: x.requires_grad, mamlGAN.parameters())
    num = sum(map(lambda x: np.prod(x.shape), tmp))
    print(mamlGAN)
    print('Total trainable tensors:', num)
    ckdir = '/content/drive/MyDrive/ACV/MetaGan/model_step7000'
    start_step = 0
    if os.path.exists(ckdir):
        print("Start from checkpoint:")
        print("Here")
        checkpoint = torch.load(ckdir)
        start_step = 7000
        mamlGAN.load_state_dict(checkpoint['model_state_dict'])
        # print('Start from a checkpoint: {}, steps:{}'.format(ckdir, str(start_step)))
    print(mamlGAN)
    db_train = OmniglotNShot('omniglot',
                       batchsz=args.tasks_per_batch,
                       n_way=args.n_way,
                       k_shot=args.k_spt,
                       k_query=args.k_qry,
                       img_sz=args.img_sz)

    save_model = not args.no_save
    if save_model:
        now = datetime.now().replace(second=0, microsecond=0)
        path = "/content/drive/MyDrive/ACV/MetaGan/results/" + str(now) + "_omni"
        mkdir_p(path)
        file = open(path +  '/architecture.txt', 'w+')
        file.write("shared_config = " + json.dumps(shared_config) + "\n" + 
            "nway_config = " + json.dumps(nway_config) + "\n" +
            "discriminator_config = " + json.dumps(discriminator_config) + "\n" + 
            "gen_config = " + json.dumps(gen_config)  + "\n" + 
            "learn_inner_lr = " + str(args.learn_inner_lr)   + "\n" + 
            "condition_discrim = " + str(args.condition_discrim)
            )
        file.close()
    for step in range(start_step, args.epoch):
        x_spt, y_spt, x_qry, y_qry = db_train.next()
        x_spt, y_spt, x_qry, y_qry = torch.from_numpy(x_spt).to(device), torch.from_numpy(y_spt).to(device), \
                                     torch.from_numpy(x_qry).to(device), torch.from_numpy(y_qry).to(device)

        # set traning=True to update running_mean, running_variance, bn_weights, bn_bias
        accs = mamlGAN(x_spt, y_spt, x_qry, y_qry)

        if step % 30 == 0:
            print("step " + str(step))
            for key in accs.keys():
                print(key + ": " + str(accs[key]))
            if save_model:
                save_train_accs(path, accs, int(step))
        if step % 500 == 0:
            print("testing")
            accs = []
            imgs = []
            for _ in range(1000//args.tasks_per_batch):
                # test
                x_spt, y_spt, x_qry, y_qry = db_train.next('test')
                x_spt, y_spt, x_qry, y_qry = torch.from_numpy(x_spt).to(device), torch.from_numpy(y_spt).to(device), \
                                             torch.from_numpy(x_qry).to(device), torch.from_numpy(y_qry).to(device)

                # split to single task each time
                for x_spt_one, y_spt_one, x_qry_one, y_qry_one in zip(x_spt, y_spt, x_qry, y_qry):
                    test_acc, ims = mamlGAN.finetunning(x_spt_one, y_spt_one, x_qry_one, y_qry_one)
                    accs.append( test_acc)
                    imgs.append(x_spt_one.cpu().detach().numpy())
                    imgs.append(ims.cpu().detach().numpy())
                    if args.single_fast_test:
                        break
                if args.single_fast_test: 
                    break

            accs = np.array(accs).mean(axis=0).astype(np.float16)
            if save_model:
                save_test_accs(path, accs, int(step))
                imgs = np.array(imgs)
                save_imgs(path, imgs, step)

                torch.save({'model_state_dict': mamlGAN.state_dict()}, path + "/model_step" + str(step))
                # to load, do this:
                # checkpoint = torch.load(path + "/model_step" + str(step))
                # mamlGAN.load_state_dict(checkpoint['model_state_dict'])


            # [b, update_steps+1]
            accs = np.array(accs).mean(axis=0).astype(np.float16)
            print('Test acc:', accs)


if __name__ == '__main__':

    argparser = argparse.ArgumentParser()
    argparser.add_argument('--epoch', type=int, help='epoch number', default=40000)
    argparser.add_argument('--n_way', type=int, help='n way', default=20)
    argparser.add_argument('--k_spt', type=int, help='k shot for support set', default=1)
    argparser.add_argument('--k_qry', type=int, help='k shot for query set', default=15)
    argparser.add_argument('--img_sz', type=int, help='img_sz', default=28)
    argparser.add_argument('--img_c', type=int, help='img_c', default=1)
    argparser.add_argument('--tasks_per_batch', type=int, help='meta batch size, i.e. number of tasks per batch', default=32)
    argparser.add_argument('--meta_lr', type=float, help='meta-level outer learning rate', default=1e-3)
    argparser.add_argument('--update_lr', type=float, help='task-level inner update learning rate', default=0.4)
    argparser.add_argument('--gan_update_lr', type=float, help='task-level inner update learning rate', default=0.4)
    argparser.add_argument('--update_steps', type=int, help='task-level inner update steps', default=5)
    argparser.add_argument('--update_steps_test', type=int, help='update steps for finetunning', default=10)
    argparser.add_argument('--no_save', default=False, action='store_true', help='Bool type. Pass to not save (right now we save by default)')
    argparser.add_argument('--learn_inner_lr', default=False, action='store_true', help='Bool type. Pass to learn inner lr')
    argparser.add_argument('--condition_discrim', default=False, action='store_true', help='Bool type. Pass to remove n_way loss from generator and condition discriminator')
    argparser.add_argument('--create_graph', default=False, action='store_true', help='Sets the "create_graph" flag for the inner gradients')
    argparser.add_argument('--loss', default="wasserstein", help='can use "wasserstein"')
    argparser.add_argument('--single_fast_test', default=False, action='store_true', help='Do one really fast test instead of waiting for tons of examples')
    argparser.add_argument('--gen_reg_w', type=float, help='regularize generator to be meta-helpful', default=0.0)

    args = argparser.parse_args()

    main(args)



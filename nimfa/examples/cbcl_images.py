
"""
    ######################################
    Cbcl_images (``examples.cbcl_images``)
    ######################################
    
    In this example of image processing we consider the problem demonstrated in [Lee1999]_.
    
    We used the CBCL face images database consisting of 2429 face images of size 19 x 19. The facial images 
    consist of frontal views hand aligned in a 19 x 19 grid. Each face image is preprocessed. For each image, 
    the greyscale intensities are first linearly scaled, so that the pixel mean and standard deviation are
    equal to 0.25, and then clipped to the range [0, 1].  
    
    .. note:: The CBCL face images database used in this example is not included in the `datasets`. If you wish to
              perform the CBCL data experiments, start by downloading the images.  Download links are listed in the 
              ``datasets``. To run the example, uncompress the data and put it into corresponding data directory, namely 
              the extracted CBCL data set must exist in the ``CBCL_faces`` directory under ``datasets``. Once you have 
              the data installed, you are ready to start running the experiments. 
      
    We experimented with the following factorization algorithms to learn the basis images from the CBCL database: 
    Standard NMF - Euclidean, LSNMF, SNMF/R and SNMF/L. The number of bases is 49. Random Vcol algorithm is used for factorization
    initialization. The algorithms mostly converge after less than 50 iterations. 
     
    Unlike vector quantization and principal components analysis ([Lee1999]_), these algorithms learn a parts-based representations of 
    faces and some also spatially localized representations depending on different types of constraints on basis and mixture matrix. 
    Following are 7 x 7 montages of learned basis images by different factorization algorithms. 
      
    .. figure:: /images/cbcl_faces_50_iters_LSNMF.png
       :scale: 90 %
       :alt: Basis images of LSNMF obtained after 50 iterations on original CBCL face images. 
       :align: center
       
       Basis images of LSNMF obtained after 50 iterations on original CBCL face images. The bases trained by LSNMF are additive
       but not spatially localized for representation of faces. 10 subiterations and 10 inner subiterations are performed
       (these are LSNMF specific parameters). 
       
       
    .. figure:: /images/cbcl_faces_50_iters_NMF.png
       :scale: 90 %
       :alt: Basis images of NMF obtained after 50 iterations on original CBCL face images. 
       :align: center
       
       Basis images of NMF obtained after 50 iterations on original CBCL face images. The images show that
       the bases trained by NMF are additive but not spatially localized for representation of faces. 
       
        
    .. figure:: /images/cbcl_faces_10_iters_SNMF_L.png
       :scale: 90 %
       :alt: Basis images of LSNMF obtained after 10 iterations on original CBCL face images. 
       :align: center
       
       Basis images of SNMF/L obtained after 10 iterations on original CBCL face images. The
       bases trained from LSNMF/L are both additive and spatially localized for representing faces. LSNMF/L imposes
       sparseness constraints on basis matrix, whereas LSNMF/R imposes sparseness on mixture matrix. Therefore obtained basis images
       are very sparse as it can be shown in the figure. The Euclidean distance of SNMF/L estimate from target matrix is 1827.66.  
       
       
    .. figure:: /images/cbcl_faces_10_iters_SNMF_R.png
       :scale: 90 %
       :alt: Basis images of SNMF/R obtained after 10 iterations on original CBCL face images. 
       :align: center
       
       Basis images of SNMF/R obtained after 10 iterations on original CBCL face images. The images show that
       the bases trained by NMF are additive but not spatially localized for representation of faces. The Euclidean
       distance of SNMF/R estimate from target matrix is 3948.149. 
       
          
    To run the example simply type::
        
        python cbcl_images.py
        
    or call the module's function::
    
        import nimfa.examples
        nimfa.examples.cbcl_images.run()
        
    .. note:: This example uses ``matplotlib`` library for producing visual interpretation of basis vectors. It uses PIL 
              library for displaying face images. 
    
"""

import nimfa
import numpy as np
from os.path import dirname, abspath, sep
from warnings import warn

try:
    from matplotlib.pyplot import savefig, imshow, set_cmap
except ImportError, exc:
    warn("Matplotlib must be installed to run CBCL images example.")

try:
    from PIL.Image import open, fromarray, new
    from PIL.ImageOps import expand
except ImportError, exc:
    warn("PIL must be installed to run CBCL images example.")


def run():
    """Run LSNMF on CBCL faces data set."""
    # read face image data from ORL database
    V = read()
    # preprocess ORL faces data matrix
    V = preprocess(V)
    # run factorization
    W, _ = factorize(V)
    # plot parts-based representation
    plot(W)


def factorize(V):
    """
    Perform LSNMF factorization on the CBCL faces data matrix. 
    
    Return basis and mixture matrices of the fitted factorization model. 
    
    :param V: The CBCL faces data matrix. 
    :type V: `numpy.matrix`
    """
    model = nimfa.mf(V,
                     seed="random_vcol",
                     rank=49,
                     method="lsnmf",
                     max_iter=50,
                     initialize_only=True,
                     sub_iter=10,
                     inner_sub_iter=10,
                     beta=0.1,
                     min_residuals=1e-8)
    print "Performing %s %s %d factorization ..." % (model, model.seed, model.rank)
    fit = nimfa.mf_run(model)
    print "... Finished"
    sparse_w, sparse_h = fit.fit.sparseness()
    print """Stats:
            - iterations: %d
            - final projected gradients norm: %5.3f
            - Euclidean distance: %5.3f 
            - Sparseness basis: %5.3f, mixture: %5.3f""" % (fit.fit.n_iter, fit.distance(), fit.distance(metric='euclidean'), sparse_w, sparse_h)
    return fit.basis(), fit.coef()


def read():
    """
    Read face image data from the CBCL database. The matrix's shape is 361 (pixels) x 2429 (faces). 
    
    Step through each subject and each image. Images' sizes are not reduced.  
    
    Return the CBCL faces data matrix. 
    """
    print "Reading CBCL faces database ..."
    dir = dirname(dirname(abspath(__file__))) + sep + \
        'datasets' + sep + 'CBCL_faces' + sep + 'face'
    V = np.matrix(np.zeros((19 * 19, 2429)))
    for image in xrange(2429):
        im = open(dir + sep + "face0" + str(image + 1).zfill(4) + ".pgm")
        V[:, image] = np.mat(np.asarray(im).flatten()).T
    print "... Finished."
    return V


def preprocess(V):
    """
    Preprocess CBCL faces data matrix as Lee and Seung.
    
    Return normalized and preprocessed data matrix. 
    
    :param V: The CBCL faces data matrix. 
    :type V: `numpy.matrix`
    """
    print "Preprocessing data matrix ..."
    V = V - V.mean()
    V = V / np.sqrt(np.multiply(V, V).mean())
    V = V + 0.25
    V = V * 0.25
    V = np.minimum(V, 1)
    V = np.maximum(V, 0)
    print "... Finished."
    return V


def plot(W):
    """
    Plot basis vectors.
    
    :param W: Basis matrix of the fitted factorization model.
    :type W: `numpy.matrix`
    """
    set_cmap('gray')
    blank = new("L", (133 + 6, 133 + 6))
    for i in xrange(7):
        for j in xrange(7):
            basis = np.array(W[:, 7 * i + j])[:, 0].reshape((19, 19))
            basis = basis / np.max(basis) * 255
            basis = 255 - basis
            ima = fromarray(basis)
            ima = ima.rotate(180)
            expand(ima, border=1, fill='black')
            blank.paste(ima.copy(), (j * 19 + j, i * 19 + i))
    imshow(blank)
    savefig("cbcl_faces.png")

if __name__ == "__main__":
    """Run the CBCL faces example."""
    run()

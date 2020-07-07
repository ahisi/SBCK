# -*- coding: utf-8 -*-

##################################################################################
##################################################################################
##                                                                              ##
## Copyright Yoann Robin, 2019                                                  ##
##                                                                              ##
## yoann.robin.k@gmail.com                                                      ##
##                                                                              ##
## This software is a computer program that is part of the SBCK (Statistical    ##
## Bias Correction Kit). This library makes it possible to perform bias         ##
## correction with non parametric methods, and give some metrics between Sparse ##
## Histogram is high dimensions.                                                ##
##                                                                              ##
## This software is governed by the CeCILL-C license under French law and       ##
## abiding by the rules of distribution of free software.  You can  use,        ##
## modify and/ or redistribute the software under the terms of the CeCILL-C     ##
## license as circulated by CEA, CNRS and INRIA at the following URL            ##
## "http://www.cecill.info".                                                    ##
##                                                                              ##
## As a counterpart to the access to the source code and  rights to copy,       ##
## modify and redistribute granted by the license, users are provided only      ##
## with a limited warranty  and the software's author,  the holder of the       ##
## economic rights,  and the successive licensors  have only  limited           ##
## liability.                                                                   ##
##                                                                              ##
## In this respect, the user's attention is drawn to the risks associated       ##
## with loading,  using,  modifying and/or developing or reproducing the        ##
## software by the user in light of its specific status of free software,       ##
## that may mean  that it is complicated to manipulate,  and  that  also        ##
## therefore means  that it is reserved for developers  and  experienced        ##
## professionals having in-depth computer knowledge. Users are therefore        ##
## encouraged to load and test the software's suitability as regards their      ##
## requirements in conditions enabling the security of their systems and/or     ##
## data to be ensured and,  more generally, to use and operate it in the        ##
## same conditions as regards security.                                         ##
##                                                                              ##
## The fact that you are presently reading this means that you have had         ##
## knowledge of the CeCILL-C license and that you accept its terms.             ##
##                                                                              ##
##################################################################################
##################################################################################

##################################################################################
##################################################################################
##                                                                              ##
## Copyright Yoann Robin, 2019                                                  ##
##                                                                              ##
## yoann.robin.k@gmail.com                                                      ##
##                                                                              ##
## Ce logiciel est un programme informatique faisant partie de la librairie     ##
## SBCK (Statistical Bias Correction Kit). Cette librairie permet d'appliquer   ##
## une correction de biais avec des méthodes non paramétriques, et propose      ##
## diverses metrique entre Histograme Sparse en haute dimension.                ##
##                                                                              ##
## Ce logiciel est régi par la licence CeCILL-C soumise au droit français et    ##
## respectant les principes de diffusion des logiciels libres. Vous pouvez      ##
## utiliser, modifier et/ou redistribuer ce programme sous les conditions       ##
## de la licence CeCILL-C telle que diffusée par le CEA, le CNRS et l'INRIA     ##
## sur le site "http://www.cecill.info".                                        ##
##                                                                              ##
## En contrepartie de l'accessibilité au code source et des droits de copie,    ##
## de modification et de redistribution accordés par cette licence, il n'est    ##
## offert aux utilisateurs qu'une garantie limitée.  Pour les mêmes raisons,    ##
## seule une responsabilité restreinte pèse sur l'auteur du programme, le       ##
## titulaire des droits patrimoniaux et les concédants successifs.              ##
##                                                                              ##
## A cet égard  l'attention de l'utilisateur est attirée sur les risques        ##
## associés au chargement,  à l'utilisation,  à la modification et/ou au        ##
## développement et à la reproduction du logiciel par l'utilisateur étant       ##
## donné sa spécificité de logiciel libre, qui peut le rendre complexe à        ##
## manipuler et qui le réserve donc à des développeurs et des professionnels    ##
## avertis possédant  des  connaissances  informatiques approfondies.  Les      ##
## utilisateurs sont donc invités à charger  et  tester  l'adéquation  du       ##
## logiciel à leurs besoins dans des conditions permettant d'assurer la         ##
## sécurité de leurs systèmes et ou de leurs données et, plus généralement,     ##
## à l'utiliser et l'exploiter dans les mêmes conditions de sécurité.           ##
##                                                                              ##
## Le fait que vous puissiez accéder à cet en-tête signifie que vous avez       ##
## pris connaissance de la licence CeCILL-C, et que vous en avez accepté les    ##
## termes.                                                                      ##
##                                                                              ##
##################################################################################
##################################################################################

###############
## Libraries ##
###############

import numpy       as np
import scipy.stats as sc
from .tools.__tools_cpp           import SparseHist
from .tools.__bin_width_estimator import bin_width_estimator
from .tools.__OT                  import OTNetworkSimplex
from .tools.__OT                  import OTSinkhornLogDual


###########
## Class ##
###########

class OTC:
	"""
	SBCK.OTC
	========
	
	Description
	-----------
	Optimal Transport bias Corrector, see [1]
	
	References
	----------
	[1] Robin, Y., Vrac, M., Naveau, P., Yiou, P.: Multivariate stochastic bias corrections with optimal transport, Hydrol. Earth Syst. Sci., 23, 773–786, 2019, https://doi.org/10.5194/hess-23-773-2019
	"""
	
	def __init__( self , bin_width = None , bin_origin = None , ot = OTNetworkSimplex() ):##{{{
		"""
		Initialisation of Optimal Transport bias Corrector.
		
		Parameters
		----------
		bin_width  : np.array( [shape = (n_features) ] )
			Lenght of bins, see SBCK.SparseHist. If is None, it is estimated during the fit
		bin_origin : np.array( [shape = (n_features) ] )
			Corner of one bin, see SBCK.SparseHist. If is None, np.repeat(0,n_features) is used
		ot         : OT*Solver*
			A solver for Optimal transport, default is OTSinkhornLogDual()
		
		Attributes
		----------
		muY	: SBCK.SparseHist
			Multivariate histogram of references
		muX	: SBCK.SparseHist
			Multivariate histogram of biased dataset
		"""
		
		self.muX = None
		self.muY = None
		self.bin_width  = bin_width
		self.bin_origin = bin_origin
		self._plan       = None
		self._ot         = ot
	##}}}
	
	def fit( self , Y0 , X0 ):##{{{
		"""
		Fit the OTC model
		
		Parameters
		----------
		Y0	: np.array[ shape = (n_samples,n_features) ]
			Reference dataset
		X0	: np.array[ shape = (n_samples,n_features) ]
			Biased dataset
		"""
		
		## Sparse Histogram
		self.bin_width  = np.array( [self.bin_width ] ).ravel() if self.bin_width  is not None else bin_width_estimator( [Y0,X0] )
		self.bin_origin = np.array( [self.bin_origin] ).ravel() if self.bin_origin is not None else np.zeros( self.bin_width.size )
		
		self.bin_width  = np.array( [self.bin_width] ).ravel()
		self.bin_origin = np.array( [self.bin_origin] ).ravel()
		
		self.muY = SparseHist( Y0 , bin_width = self.bin_width , bin_origin = self.bin_origin )
		self.muX = SparseHist( X0 , bin_width = self.bin_width , bin_origin = self.bin_origin )
		
		
		## Optimal Transport
		self._ot.fit( self.muX , self.muY )
		if not self._ot.state:
			print( "Warning: Error in network simplex, try SinkhornLogDual" )
			self._ot = OTSinkhornLogDual()
			self._ot.fit( self.muX , self.muY )
		
		## 
		self._plan = np.copy( self._ot.plan() )
		self._plan = ( self._plan.T / self._plan.sum( axis = 1 ) ).T
	##}}}
	
	def predict( self , X0 ):##{{{
		"""
		Perform the bias correction
		
		Parameters
		----------
		X0  : np.array[ shape = (n_samples,n_features) ]
			Array of values to be corrected
		
		Returns
		-------
		Z0 : np.array[ shape = (n_samples,n_features) ]
			Return an array of correction
		"""
		indx = self.muX.argwhere(X0)
		indy = np.zeros_like(indx)
		for i,ix in enumerate(indx):
			indy[i] = np.random.choice( range(self.muY.size) , p = self._plan[ix,:] )
		return self.muY.c[indy,:]
	##}}}




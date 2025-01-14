# -*- coding: utf-8 -*-

## Copyright(c) 2021 Yoann Robin
## 
## This file is part of SBCK.
## 
## SBCK is free software: you can redistribute it and/or modify
## it under the terms of the GNU General Public License as published by
## the Free Software Foundation, either version 3 of the License, or
## (at your option) any later version.
## 
## SBCK is distributed in the hope that it will be useful,
## but WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
## GNU General Public License for more details.
## 
## You should have received a copy of the GNU General Public License
## along with SBCK.  If not, see <https://www.gnu.org/licenses/>.

###############
## Libraries ##
###############

import numpy as np
import scipy.stats as sc
import scipy.interpolate as sci


#############
## Classes ##
#############

class MonotoneInverse:##{{{
	
	def __init__( self , xminmax , yminmax , transform ):##{{{
		self.xmin  = xminmax[0]
		self.xmax  = xminmax[1]
		self.ymin  = yminmax[0]
		self.ymax  = yminmax[1]
		delta = 0.05 * (self.xmax - self.xmin)
		nstepmin,nstepmax = 0,0
		while transform(self.xmin) > self.ymin:
			self.xmin -= delta
			nstepmin += 1
		while transform(self.xmax) < self.ymax:
			self.xmax += delta
			nstepmax += 1
		self.nstep = 100 + max(nstepmin,nstepmax)
		x = np.linspace(self.xmin,self.xmax,self.nstep)
		y = transform(x)
		self._inverse = sci.interp1d( y , x )
	##}}}
	
	def __call__( self , y ):##{{{
		return self._inverse(y)
	##}}}

##}}}

class rv_histogram(sc.rv_histogram):##{{{
	"""
	SBCK.tools.rv_histogram
	=======================
	Wrapper on scipy.stats.rv_histogram adding a fit method.
	"""
	def __init__( self , *args , **kwargs ):##{{{
		sc.rv_histogram.__init__( self , *args , **kwargs )
	##}}}
	
	def fit( X , bins = 100 ):##{{{
		return (np.histogram( X , bins = bins ),)
	##}}}
	
##}}}

class rv_ratio_histogram(sc.rv_histogram):##{{{
	"""
	SBCK.tools.rv_ratio_histogram
	=============================
	Extension of SBCK.tools.rv_histogram taking into account of a "ratio" part, i.e., instead of fitting:
	P( X < x )
	We fit separatly the frequency of 0 and:
	P( X < x | X > 0 )
	"""
	def __init__( self , *args , **kwargs ):##{{{
		eargs = ()
		if len(args) > 0:
			eargs = (args[0],)
		sc.rv_histogram.__init__( self , *eargs , **kwargs )
		self.p0 = 0
		if len(args) > 1:
			self.p0 = args[1]
	##}}}
	
	def fit( X , bins = 100 ):##{{{
		Xp = X[X>0]
		p0 = np.sum(np.logical_not(X>0)) / X.size
		return (np.histogram( Xp , bins = bins ),p0)
	##}}}
	
	def cdf( self , x ):##{{{
		cdf = np.zeros_like(x)
		idxp = x > 0
		idx0 = np.logical_not(x>0)
		cdf[idxp] = (1-self.p0) * sc.rv_histogram.cdf( self , x[idxp] ) + self.p0
		cdf[idx0] = self.p0 / 2
		return cdf
	##}}}
	
	def ppf( self , p ):##{{{
		idxp = p > self.p0
		idx0 = np.logical_not(p > self.p0 )
		ppf = np.zeros_like(p)
		ppf[idxp] = sc.rv_histogram.ppf( self , (p[idxp] - self.p0) / (1-self.p0) )
		ppf[idx0] = 0
		return ppf
	##}}}
	
	def sf( self , x ):##{{{
		return 1 - self.cdf(x)
	##}}}
	
	def isf( self , p ):##{{{
		return self.ppf( 1 - p )
	##}}}

##}}}

class rv_density:##{{{
	
	def __init__( self , *args , **kwargs ):##{{{
		self._kernel = None
		if kwargs.get("X") is not None:
			X = kwargs.get("X")
			self._kernel = sc.gaussian_kde( X.squeeze() , bw_method = kwargs.get("bw_method") )
			self._init_icdf( [X.min(),X.max()] )
		elif len(args) > 0:
			self._kernel = args[0]
			self._init_icdf( [args[1],args[2]] )
	##}}}
	
	def rvs( self , size ):##{{{
		p = np.random.uniform( size = size )
		return self.icdf(p)
	##}}}
	
	def fit( X , bw_method = None ):##{{{
		kernel = sc.gaussian_kde( X , bw_method = bw_method )
		return (kernel,X.min(),X.max())
	##}}}
	
	def pdf( self , x ):##{{{
		return self._kernel.pdf(x)
	##}}}
	
	def cdf( self , x ):##{{{
		x = np.array([x]).squeeze().reshape(-1,1)
		cdf = np.apply_along_axis( lambda z: self._kernel.integrate_box_1d( -np.Inf , z ) , 1 , x )
		cdf[cdf < 0] = 0
		cdf[cdf > 1] = 1
		return cdf.squeeze()
	##}}}
	
	def sf( self , x ):##{{{
		return 1 - self.cdf(x)
	##}}}
	
	def ppf( self , q ):##{{{
		return self.icdf(q)
	##}}}
	
	def icdf( self , q ):##{{{
		return self._icdf_fct(q)
	##}}}
	
	def isf( self , q ):##{{{
		return self.icdf(1-q)
	##}}}
	
	def _init_icdf( self , xminmax ):##{{{
		self._icdf_fct = MonotoneInverse( xminmax , [0,1] , self.cdf )
	##}}}

##}}}

class rv_mixture:##{{{
	
	def __init__( self , l_dist , weights = None ):##{{{
		self._l_dist  = l_dist
		self._n_dist  = len(l_dist)
		self._weights = np.array([weights]).squeeze() if weights is not None else np.ones(self._n_dist)
		self._weights /= self._weights.sum()
		self._init_icdf()
	##}}}
	
	def rvs( self , size ):##{{{
		out = np.zeros(size)
		ib,ie = 0,int(self._weights[0]*size)
		for i in range(self._n_dist-1):
			out[ib:ie] = self._l_dist[i].rvs( size = ie - ib )
			next_size = int(self._weights[i+1]*size)
			ib,ie = ie,min(ie+next_size,size)
		out[ib:] = self._l_dist[-1].rvs( size = size - ib )
		
		return out[np.random.choice(size,size,replace = False)]
	##}}}
	
	def pdf( self , x ):##{{{
		x = np.array([x]).reshape(-1,1)
		dens = np.zeros_like(x)
		for i in range(self._n_dist):
			dens += self._l_dist[i].pdf(x) * self._weights[i]
		return dens
	##}}}
	
	def cdf( self , x ):##{{{
		x = np.array([x]).reshape(-1,1)
		cdf = np.zeros_like(x)
		for i in range(self._n_dist):
			cdf += self._l_dist[i].cdf(x) * self._weights[i]
		return cdf.squeeze()
	##}}}
	
	def sf( self , x ):##{{{
		return 1 - self.cdf(x)
	##}}}
	
	def ppf( self , q ):##{{{
		return self.icdf(q)
	##}}}
	
	def icdf( self , q ):##{{{
		q = np.array([q]).reshape(-1,1)
		return self._icdf_fct(q)
	##}}}
	
	def _init_icdf(self):##{{{
		rvs = self.rvs(10000)
		self._icdf_fct = MonotoneInverse( [rvs.min(),rvs.max()] , [0,1] , self.cdf )
	##}}}
	
	def isf( self , q ):##{{{
		return self.icdf(1-q)
	##}}}
	
##}}}



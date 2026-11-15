"""Funciones extraídas del análisis original.
Único cambio de firma: RONI se recibe como parámetro, sin variable global.
No importar analyze.py en el servidor: aquel script ejecuta todo el backtest.
"""
import numpy as np
import pandas as pd

def predict_models(s,origin,horizons,roni):
 train=s.iloc[:origin+1];ix=train.index;y=train.values;n=len(y);last=ix[-1]
 targets=[last+pd.DateOffset(months=h) for h in horizons];mo=np.array([x.month-1 for x in targets])
 def monthly(a):return np.array([a[a.index.month==m].mean() for m in range(1,13)])
 c10=monthly(train.iloc[-120:]);c30=monthly(train.iloc[-360:]);naive=np.array([float(train.loc[t-pd.DateOffset(years=1)]) if t-pd.DateOffset(years=1)<=last else c10[t.month-1] for t in targets])
 recent=train.iloc[-240:];tt=np.arange(len(recent))/120;X=np.column_stack([np.eye(12)[recent.index.month-1],tt]);beta=np.linalg.lstsq(X,recent.values,rcond=None)[0];res=recent.values-X@beta
 xfuture=np.column_stack([np.eye(12)[mo],(len(recent)-1+np.array(horizons))/120]);trend=xfuture@beta
 phi=np.clip(np.dot(res[:-1],res[1:])/max(np.dot(res[:-1],res[:-1]),1e-12),-.98,.98)
 out={'clim10':c10[mo],'clim30':c30[mo],'seasonal_naive':naive,'trend20':trend,'trend20_ar1':trend+phi**np.array(horizons)*res[-1]}
 rz=roni.shift(1,freq='MS').reindex(recent.index).values
 ens=[]
 for k,h in enumerate(horizons):
  xx=np.column_stack([res[:-h],rz[:-h]]);yy=res[h:];valid=np.isfinite(xx).all(axis=1)
  x=xx[valid];z=yy[valid];mean=x.mean(0);scale=x.std(0);scale[scale<1e-8]=1
  xd=np.column_stack([np.ones(len(x)),(x-mean)/scale]);reg=np.diag([0.,10.,10.]);coef=np.linalg.solve(xd.T@xd+reg,xd.T@z)
  pred=coef@np.r_[1.,(np.array([res[-1],rz[-1]])-mean)/scale]
  ens.append(trend[k]+pred)
 out['trend20_enso_direct']=np.array(ens)
 # The target month's historical variability sets the interval scale.
 sig=np.array([recent[recent.index.month==m].std(ddof=1) for m in range(1,13)])[mo]
 return out,sig,targets

def physical(v,var):return np.clip(v,0,100) if var=='RH2M' else np.maximum(v,0) if var in ['PRECTOTCORR','UV'] else v

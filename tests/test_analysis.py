import numpy as np
import pandas as pd
from airbnb_lab.analysis import hypotheses, cluster_mean_ci, models
from airbnb_lab.quality import clean_inputs
from test_quality import inputs


def test_missing_calendar_price_is_not_fabricated():
    t,_=clean_inputs(inputs(),{'snapshot_date':'2026-09-14'})
    result=hypotheses(t['listings'],t['calendar'])
    h5=next(x for x in result if x['id']=='H5')
    assert h5['status']=='not estimable'
    assert 'p_value' not in h5


def test_cluster_interval_is_reproducible_and_suppresses_small_groups():
    df=pd.DataFrame({'host_id':list('abcdef')*2,'price':[10,20,30,40,50,60]*2})
    assert cluster_mean_ci(df,42)==cluster_mean_ci(df,42)
    low,high=cluster_mean_ci(df,42)
    assert low<35<high
    assert cluster_mean_ci(df.iloc[:3])==(None,None)


def test_model_contract_and_no_target_derived_features():
    rng=np.random.default_rng(7)
    n=90
    df=pd.DataFrame({'host_id':[str(i//3) for i in range(n)],'price':rng.uniform(50,200,n),
                     'accommodates':rng.integers(1,6,n),'bedrooms':rng.integers(1,4,n),'bathrooms':1.,'beds':2.,
                     'latitude':42.6,'longitude':-73.7,'amenity_count':20.,'host_tenure_years':3.,
                     'room_type':'entire home/apt','property_type':'apartment','neighbourhood':'first ward'})
    result,errors,importance=models(df,42)
    assert result['host_overlap']==0
    assert result['train_hosts']+result['test_hosts']==30
    assert len(result['scores'])==4
    assert result['selected_model']==min(result['scores'],key=lambda r:r['cv_mae'])['model']
    assert 'price_per_bedroom' not in result['features']
    assert 'price' not in result['features']
    assert len(errors)==result['test_rows']

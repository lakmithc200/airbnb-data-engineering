import pandas as pd
import pytest
from airbnb_lab.quality import money, clean_inputs, bathrooms_from_text


def inputs():
    listings = pd.DataFrame({
        "id":["9007199254740993","9007199254740995"],"host_id":["11","12"],
        "price":["$1,234.50","$80.00"],"room_type":["Entire home/apt","Private room"],
        "neighbourhood_cleansed":[" First  Ward ","Second Ward"],"latitude":["42.6","42.7"],
        "longitude":["-73.7","-73.8"],"bedrooms":["0","2"],"accommodates":["2","2"],
        "last_scraped":["2026-09-16"]*2,"host_since":["2020-01-01"]*2,
        "number_of_reviews":["1","0"],"review_scores_rating":["4.8",None],
        "host_is_superhost":["t","f"]},dtype="string")
    calendar=pd.DataFrame({"listing_id":["9007199254740993"]*3,"date":["2026-09-16","2026-09-17","2026-09-18"],"available":["t","f","unknown"]},dtype="string")
    reviews=pd.DataFrame({"id":["7000000000000001"],"listing_id":["9007199254740993"],"date":["2026-09-15"],"reviewer_name":["Sensitive person"],"comments":["Private sample text"]},dtype="string")
    return {"listings":listings,"calendar":calendar,"reviews":reviews}


def test_money_does_not_guess_ambiguous_formats():
    out=money(pd.Series(["$1,234.56"," 80.25 ","$-3",None,"free","1,23","1e5","NaN"]))
    assert out.iloc[:3].tolist()==[1234.56,80.25,-3]
    assert out.iloc[3:].isna().all()


def test_large_ids_nullable_availability_and_privacy():
    tables,audit=clean_inputs(inputs(),{"snapshot_date":"2026-09-14"})
    l=tables['listings'].set_index('id')
    assert set(l.index)=={"9007199254740993","9007199254740995"}
    assert l.loc["9007199254740993","unavailable_share"]==.5
    assert l.loc["9007199254740993","known_days"]==2
    assert pd.isna(l.loc["9007199254740993","price_per_bedroom"])
    assert l.loc["9007199254740993","neighbourhood"]=="First Ward"
    assert audit['as_of_date']=='2026-09-16'
    assert not audit['calendar_price_column_present']
    assert tables['calendar'].price.isna().all()
    assert set(tables['reviews'])=={'id','listing_id','date'}


def test_invalid_rows_duplicates_and_domain_values():
    raw=inputs()
    raw['listings'].loc[0,'price']='-$5'
    raw['listings'].loc[1,'latitude']='100'
    raw['listings']=pd.concat([raw['listings'],raw['listings'].iloc[[1]]],ignore_index=True)
    raw['reviews']=pd.concat([raw['reviews'],pd.DataFrame({'id':['77','78'],'listing_id':['999','9007199254740993'],'date':['2026-01-01','2030-01-01']})],ignore_index=True)
    raw['calendar']=pd.concat([raw['calendar'],raw['calendar'].iloc[[0]],pd.DataFrame({'listing_id':['999'],'date':['bad'],'available':['t']})],ignore_index=True)
    t,a=clean_inputs(raw,{'snapshot_date':'2026-09-14'})
    assert len(t['listings'])==2 and len(t['reviews'])==1 and len(t['calendar'])==3
    assert a['listings_duplicate_keys_removed']==1
    assert a['reviews_invalid_future_or_orphan_rows_removed']==2
    assert a['calendar_duplicate_keys_removed']==1
    assert t['listings'].latitude.isna().sum()==1


def test_required_schema_change_fails_loudly():
    raw=inputs();raw['listings']=raw['listings'].drop(columns='id')
    with pytest.raises(ValueError,match='required columns'):
        clean_inputs(raw,{'snapshot_date':'2026-09-14'})


def test_schema_evolution_fallbacks_preserve_meaning():
    raw=inputs()
    raw['listings']['host_since']=pd.NA
    raw['listings']['hosts_time_as_user_years']=['3','4']
    raw['listings']['hosts_time_as_user_months']=['6','15']
    raw['listings']['bathrooms_text']=['1.5 shared baths','Private half-bath']
    t,a=clean_inputs(raw,{'snapshot_date':'2026-09-14'})
    assert t['listings'].bathrooms.tolist()==[1.5,.5]
    assert t['listings'].host_tenure_years.iloc[0]==3.5
    assert pd.isna(t['listings'].host_tenure_years.iloc[1])
    assert a['account_tenure_recovered_from_duration']==1
    assert pd.isna(bathrooms_from_text(pd.Series(['Ask host'])).iloc[0])

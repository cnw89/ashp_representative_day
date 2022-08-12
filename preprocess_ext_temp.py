import pandas as pd

IN_FILENAME = 'ninja_weather_country_GB_merra-2_population_weighted.csv'
OUT_FILENAME = 'Text_profiles.csv'

YEAR_RANGE = [2000, 2019]

years_to_drop = []
if YEAR_RANGE[0] > 1980:
    years_to_drop.extend([y for y in range(1980, YEAR_RANGE[0])])
if YEAR_RANGE[1] < 2019:
    years_to_drop.extend([y for y in range(YEAR_RANGE[1], 2019)])

def min_and_max_per_month(df):

    #break out date
    df = df.assign(year=df.time.dt.year, month=df.time.dt.month, day=df.time.dt.day, time_of_day=df.time.dt.time)

    #filter by years
    df.set_index('year', inplace=True)
    df.drop(index=years_to_drop, inplace=True)

    #average over years and days within the month
    df.set_index(['month', 'day', 'time_of_day'], inplace=True)
    df = df.groupby(level=[0, 1, 2]).mean() #both min and mean profiles are averaged over years first
    dfmean = df.groupby(level=[0, 2]).mean()
    dfmin = df.groupby(level=[0, 2]).min()

    # #1 month per column
    dfmean = dfmean.unstack('month')
    dfmin = dfmin.unstack('month')
    
    #join min and mean
    dfmean.columns.set_levels(['mean'],level=0,inplace=True)
    dfmin.columns.set_levels(['min'],level=0,inplace=True)
    df = pd.concat([dfmean, dfmin], axis=1)
    
    #interpolate to every 10 minutes, assuming every hour intially
    df2 = pd.DataFrame(columns=df.columns, index=pd.date_range(start='01/01/2000 00:00', end='01/02/2000 00:00', freq='10min'), dtype=float)
    df2.iloc[:-1:6, :] = df.iloc[:, :]
    df2.iloc[-1, :] = df2.iloc[0, :]    
    df2 = df2.interpolate(method='time') 

    return df2

if __name__ == "__main__":

    #first do temperatures
    df = pd.read_csv(IN_FILENAME, header=2, parse_dates=[0], infer_datetime_format=True, dayfirst=True, usecols=[0, 2])
    df2 = min_and_max_per_month(df)    
    
    df2.to_csv(OUT_FILENAME)

    #then do solar
    df = pd.read_csv(IN_FILENAME, header=2, parse_dates=[0], infer_datetime_format=True, dayfirst=True, usecols=[0, 3])
    df2 = min_and_max_per_month(df)    
    
    OUT_FILENAME = 'Psolar_profiles.csv'
    df2.to_csv(OUT_FILENAME)

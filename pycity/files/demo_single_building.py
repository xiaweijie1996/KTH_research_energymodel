# -*- coding: utf-8 -*-
"""
Created on Sun Mar  6 19:14:08 2022

@author: xiaweijie
"""
import numpy as np
import matplotlib.pyplot as plt

import pycity_base.classes.demand.domestic_hot_water as DomesticHotWater
import pycity_base.classes.demand.electrical_demand as ElectricalDemand
import pycity_base.classes.demand.space_heating as SpaceHeating

import pycity_base.classes.timer as Ti
import pycity_base.classes.weather as Weather
import pycity_base.classes.prices as Prices
import pycity_base.classes.environment as Env

import pycity_base.classes.demand.apartment as Apartment
import pycity_base.classes.building as Building

from pycity_base.functions import change_resolution as chres

import pycity_base.classes.supply.building_energy_system as BES
import pycity_base.classes.supply.boiler as Boiler
import pycity_base.classes.supply.photovoltaic as PV
import pycity_base.classes.supply.battery as BA

#   Generate timer object for environment
tii = Ti.Timer(time_discretization=3600, timesteps_total=8760)

#  Generate weather object
weather = Weather.Weather(tii)
#  Weather object holds weather data, such as outdoor temperatures,
#  Default TRY value is TRY2010_05_Jahr.dat

#  Generate price object
price = Prices.Prices()
#  Holding energy prices and subsidies

#  Generate environment object
environment = Env.Environment(timer=tii, weather=weather, prices=price)

#  Generate space heating load object
space_heating = SpaceHeating.SpaceHeating(environment, method=1,
                                          living_area=200,
                                          specific_demand=100)
#  Method 1 Use standardized load profile (SLP)
#  Annual demand is calculated product of living_area and specific_demand

#  Show space heating power curve in Watt
print('Space heating power curve in Watt:')
print(space_heating.get_power(currentValues=False))
#  currentValues = False --> Show values for all timesteps
#  (not only for forecast horizon)

# Plot curve
plt.plot(space_heating.get_power(currentValues=False))
plt.xlabel('Time in hours')
plt.ylabel('Thermal power in Watt (space heating)')
plt.title('Space heating power curve')
plt.show()

el_demand = ElectricalDemand.ElectricalDemand(environment,
                                              method=1,
                                              annual_demand=4000)

plt.plot(el_demand.get_power(currentValues=False))
plt.xlabel('Time in hours')
plt.ylabel('Load in Watt ')
plt.title('Load curve')
plt.show()

#  Generate domestic hot water object via Annex 42 data
dhw_annex42 = DomesticHotWater.DomesticHotWater(environment,
                                                t_flow=30,
                                                thermal=True,
                                                method=1,
                                                daily_consumption=40,
                                                supply_temperature=25)
plt.plot(dhw_annex42.get_power(currentValues=False, returnTemperature=False))
plt.xlabel('Time in hours')
plt.ylabel('Domestic Hot water in Watt')
plt.title('Domestic Hot water curve')
plt.show()

#  Initialize boiler object
boiler = Boiler.Boiler(environment, q_nominal=10000, eta=0.85)

# add pv and battery
pv = PV.PV(environment, method=1, peak_power=12)
ba = BA.Battery(environment, soc_init=10000, capacity=10000)

# Initialize BES object
bes = BES.BES(environment)
bes.addDevice(pv)
bes.addDevice(ba)

#  Add device (boiler) to BES
bes.addDevice(boiler)

#  Initialize apartment object
apartment = Apartment.Apartment(environment)
#  Add multiple entities to apartment
apartment.addMultipleEntities([el_demand,dhw_annex42,space_heating,bes])

#  Initialize building object
building = Building.Building(environment)

#  Add apartment (with loads) to building object
building.addEntity(entity=apartment)

  # Return space heating power curve from building
print('Show space heating power curve of building')
space_heat_curve = building.get_space_heating_power_curve()
print(space_heat_curve)

  # Return el. power curve from building
print('Show el. power curve of building')
el_power_curve = building.get_electric_power_curve()
print(el_power_curve)

  # Return hot water power curve from building
print('Show domestic hot water power curve of building')
dhw_power_curve = building.get_dhw_power_curve()
print(dhw_power_curve)

  # Convert to identical timestep (of 3600 seconds)
el_power_curve_res = chres.changeResolution(el_power_curve, 900, 3600)

#  Plot all load curves
plt.subplot(3, 1, 1)
plt.title('Load curves of building')
plt.plot(space_heat_curve)
plt.ylabel('Space heat. power in W')

plt.subplot(3, 1, 2)
plt.plot(el_power_curve_res)
plt.ylabel('El. power in W')

plt.subplot(3, 1, 3)
plt.plot(dhw_power_curve)
plt.ylabel('Hot water power in W')
plt.xlabel('Time in hours')

plt.show()
#%%
# Optimization

from pycity_scheduling.classes import *
from pycity_scheduling.algorithms import *
from pycity_scheduling.util.plot_schedules import plot_entity
from pycity_scheduling.util.metric import self_consumption

t = Timer(op_horizon=24, step_size=3600, initial_date=(2018, 3, 15), initial_time=(0, 0, 0))
w = Weather(timer=t, location=(50.76, 6.07))
p = Prices(timer=t)
e = Environment(timer=t, weather=w, prices=p)
                
fi = FixedLoad(environment=e, method=1, annual_demand=3000.0, profile_type= "H0" )
pv = Photovoltaic(environment=e, method=1, peak_power=6.0)
ba = Battery(environment=e, e_el_max=8.4, p_el_max_charge=3.6, p_el_max_discharge=3.6)

bd = Building(environment=e, objective= "none" )
bes = BuildingEnergySystem(environment=e)
ap = Apartment(environment=e)
bd.addMultipleEntities(entities=[bes, ap])
bes.addDevice(objectInstance=pv)
ap.addMultipleEntities(entities=[fi, ba])

cd = CityDistrict(e, objective= "price" )
cd.addEntity(bd, position=(0, 0))

opt = CentralOptimization(city_district=cd, mode= "integer" )
res = opt.solve()
cd.copy_schedule(dst= "optim_schedule" )

plot_entity(entity=cd, schedule=[ "optim_schedule" ], title= " City district - Cost -optimal schedules " )
plot_entity(entity=ba, schedule=[ "optim_schedule" ], title= " Battery unit - Cost -optimal schedules " )

print(self_consumption(entity=bd))

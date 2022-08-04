
class HeatSource():

    def __init__(self):
        pass

    def run(self, Tin, Tout, Tset):
        pass

class Boiler(HeatSource):
    #Todo: efficiency in terms of system temperature?
    def __init__(self, Pdesign, Ttol=1, eff=0.9, status=True):

        self.Pmax = min(3 * Pdesign, 20000)
        self.Ttol = Ttol
        self.status = status
        self.eff = eff

    def run(self, Tin, Tout, Tset):

        if self.status:

            if Tin > (Tset + self.Ttol) : 

                self.status = False
                return 0, 0

            else:
                return self.Pmax, self.Pmax/self.eff

        else:
            if Tin < (Tset - self.Ttol):

                self.status = True
                return self.Pmax, self.Pmax/self.eff

            else:
                return 0, 0 

class HeatPump(HeatSource):
    Tsys = 45
    Toff = 8
    def __init__(self, Pdesign, Ttol=1, eff=0.75, weather_control_range=[-3, 17]):
        #efficiency here is a fraction of the Carnot COP
        self.weather_control_range = weather_control_range
        self.Pmax = Pdesign
        self.Ttol = Ttol
        self.eff = eff 

    def run(self, Tin, Tout, Tset):

        if Tin > (Tset + self.Ttol):
            return 0, 0

        Pout = (self.weather_control_range[1] - Tout)/(self.weather_control_range[1] - self.weather_control_range[0])
        Pout = max(0, min(1, Pout))
        Pout *= self.Pmax

        COPideal = (273 + Tout - self.Toff)/(self.Tsys - Tout + 2 * self.Toff)
        return Pout, Pout/(self.eff * COPideal)


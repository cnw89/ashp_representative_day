
class HeatSource():

    def __init__(self):
        pass

    def run(self, Tin, Tout, Tset):
        pass

class Boiler(HeatSource):

    def __init__(self, Pdesign, Ttol=1, status=True):

        self.Pmax = min(3 * Pdesign, 20000)
        self.Ttol = Ttol
        self.status = status

    def run(self, Tin, Tout, Tset):

        if self.status:

            if Tin > (Tset + self.Ttol) : 

                self.status = False
                return 0

            else:
                return self.Pmax

        else:
            if Tin < (Tset - self.Ttol):

                self.status = True
                return self.Pmax

            else:
                return 0

class HeatPump(HeatSource):

    def __init__(self, Pdesign, Ttol=1, weather_control_range=[-3, 17]):

        self.weather_control_range = weather_control_range
        self.Pmax = Pdesign
        self.Ttol = Ttol

    def run(self, Tin, Tout, Tset):

        if Tin > (Tset + self.Ttol):
            return 0
        Pout = (self.weather_control_range[1] - Tout)/(self.weather_control_range[1] - self.weather_control_range[0])
        Pout = max(0, min(1, Pout))
        Pout *= self.Pmax

        return Pout


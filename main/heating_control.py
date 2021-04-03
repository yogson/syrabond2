import threading
from time import sleep


class HeatingController:

    def __init__(self):
        self.premises, self.circuits = [], []
        t = threading.Thread(target=self.worker, daemon=True)
        t.start()

    def init_resources(self):
        from .models import Premise, HeatingCircuit
        self.premises = [prem for prem in Premise.objects.filter(heating_controller__isnull=False)]
        self.circuits = [item for item in HeatingCircuit.objects.filter(premise__isnull=False)]

    def check_compliance(self):
        self.init_resources()
        for prem in self.premises:
            print(prem.title, prem.thermostat, prem.temp)
            if isinstance(prem.temp, float):
                if prem.temp <= prem.thermostat:
                    for circuit in self.circuits:
                        circuit.open()
                else:
                    for circuit in self.circuits:
                        circuit.close()

    def worker(self, sleep_time=3):
        while True:
            sleep(sleep_time)
            self.check_compliance()


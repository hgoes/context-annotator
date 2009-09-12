def gcd(a,b):
    while(a):
        a, b = b % a, a
    return b

class Colors:
    def __init__(self):
        self.divisor = 1
        self.r = 0
        self.g = 0
        self.b = 0
    def step(self):
        if self.r == self.divisor:
            self.r = 0
            if self.g == self.divisor:
                self.g = 0
                if self.b == self.divisor:
                    self.b = 0
                    self.divisor += 1
                else:
                    self.b += 1
            else:
                self.g += 1
        else:
            self.r += 1
    def valid(self):
        if self.r == self.g and self.g == self.b:
            return False
        if gcd(self.r,self.divisor) != 1 and gcd(self.g,self.divisor) != 1 and gcd(self.b,self.divisor) != 1:
            return False
        return True
    def next(self):
        while not self.valid():
            self.step()
        r,g,b = float(self.r)/self.divisor,float(self.g)/self.divisor,float(self.b)/self.divisor
        self.step()
        return r,g,b
        
            

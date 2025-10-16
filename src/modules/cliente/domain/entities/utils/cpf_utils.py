import re

class ValidateCpf:
    
    @staticmethod
    def validate_cpf(cpf: str):
        cpf = re.sub(r'\D', '', cpf)

        if len(cpf) != 11:
            raise ValueError("CPF deve ter 11 dígitos")

        if cpf == cpf[0] * 11:
            raise ValueError("CPF inválido")

        sum1 = sum(int(cpf[i]) * (10 - i) for i in range(9))
        check1 = (sum1 * 10 % 11) % 10
        
        sum2 = sum(int(cpf[i]) * (11 - i) for i in range(10))
        check2 = (sum2 * 10 % 11) % 10

        if check1 != int(cpf[9]) or check2 != int(cpf[10]):
            raise ValueError("CPF inválido")
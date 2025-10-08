import re

class ValidateCpfCnpj:
    
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

    @staticmethod
    def validate_cnpj(cnpj: str):
        cnpj = re.sub(r'\D', '', cnpj)

        if len(cnpj) != 14:
            raise ValueError("CNPJ deve ter 14 dígitos")

        if cnpj == cnpj[0] * 14:
            raise ValueError("CNPJ inválido")

        def calculate_digit(cnpj, weights):
            total = sum(int(cnpj[i]) * weights[i] for i in range(len(weights)))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder

        first_weights = [5,4,3,2,9,8,7,6,5,4,3,2]
        second_weights = [6] + first_weights

        digit1 = calculate_digit(cnpj, first_weights)
        digit2 = calculate_digit(cnpj, second_weights)

        if digit1 != int(cnpj[12]) or digit2 != int(cnpj[13]):
            raise ValueError("CNPJ inválido")

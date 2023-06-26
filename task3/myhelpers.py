def validate_credit(card_number):

    def check_sum(credit_number):
        # Implement check_sum logic here
        sum = 0
        digit = 0

        while (credit_number > 0):
            temp = credit_number%10
            credit_number = credit_number//10

            if digit%2==0:
                sum += temp
            else:
                temp = 2*temp
                sum += temp%10
                sum += temp//10
            digit+=1
        return sum

    temp_credit = card_number
    total_sum = check_sum(card_number)
    counter = len(str(card_number))

    if total_sum % 10 == 0:
        amex_start = temp_credit // 10000000000000
        if amex_start == 34 or amex_start == 37 and counter == 15:
            return "AMEX"

        master_card = temp_credit // 100000000000000
        if 55 >= master_card >= 51:
            return "MASTER"

        visa_start = temp_credit // 1000000000000
        if visa_start == 4 or master_card // 10 == 4 and (counter == 13 or counter == 16):
            return "VISA"
    else:
        return "INVALID"
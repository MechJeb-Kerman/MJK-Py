month=(input("Enter month: "))
if month=="February":
    print("28 days")
elif month in ["April", "June", "September", "November"]:
    print("30 days")
else:
    print("31 days")

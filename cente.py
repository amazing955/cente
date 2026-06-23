Print, Separator,\n, endprint(values,sep=' ',end='\n' , file=sys.stdout,flush=False);
print(10,20,30,40,50,60,70,80,90, sep='\n',end='#')

float division
a=4/3
print(a)

int division
a=4//3
print(a)

#exponet operator
a=5**2
print(a)

#Relational operators
syntax= opr1 if opr2 else opr3
print("true") if 100<20 else print("false")
a=int(input("enter a number"))
b=int(input("enter a second number"))
print("numbers are equal") if a==b else print("numbers not equal")

#a=int(input("enter a number"))





print("the number is even") if a%2 == 0 else print("odd")
a=3
b=2
c=(d:=a+b)
print(c)
n=int(input("enter number"))
print("the number is even") if ((r:=n%2) == 0) else print("odd")
 
#simple if
if(100>20):
    print("true")
    print("Welcome bro")
  
  
If else  
if(1>20):
    print("true")
    print("Welcome bro")    
else:
    print("bro you failed me")
 
 
#vote example 
name=input("name")
age=int(input("enter years"))
if(age>=20):
    print("voter")
else:    
    print("ooooh no")
 
 
 
 #ladder if
age=int(input("enter years"))
if(age<=13):
    print("not teenager")
elif(age>13 and age<20):
 print("teenager")
elif(age>=20 and age<36):
  print("youth")
else:    
    print("elder")    


marks=int(input("enter marks"))
if(marks>90 and marks<100):
   print("A")
elif(marks>80 and marks<90):
 print("B")
elif(marks>=60 and marks<=80):
  print("C")
elif(marks<60 and marks>=0):
  print("D")
else:    
   print("invalid")    

password sample
name=input("name")
pasword=input("enter password")
if(name=="clint"):
  if(pasword=="123"):  
    print("Welcome")
  else:    
    print("invalid password")
else:
    print("invalid username")


a=int(input("enter first number"))
b=int(input("enter second number"))
c=int(input("enter third number"))

if a>b:
    if a>c:
        print(a, "is max")
    else:
        print(b, "is max")
elif b>c:
    if b>a:
        print(b, "is max")
    else:
        print(c, "is max")
elif c>a:
    if c>b:
        print(c, "is max")
    else:
        print(b, "is max")
        
else:
    print("equal")
 
print("*****CALCULATOR****")
print("1.Add")
print("2.Sub")
print("3.Multiply")
print("4.Divide")
print("\n******WORKSPACE******")
opt=int(input("enter your option"))

num1=int(input("enter first number"))
 
num2=int(input("enter second number"))
 
match(opt):
     case 1:
         print('sum is ',num1+num2)
     case 2:
         print('diff is ',num1-num2)
     case 3:
         print('product is ',num1*num2)
     case 3:
         print('result is ',num1/num2)    
     case _:
         print("error")
                
                
print("*****AREA****")
print("1.Circle")
print("2.Triangle")
mike=int(input("enter your option"))
match(mike):
     case 1:
         r=float(input("enter radius"))
         print('area is ',3.147*r*r)
     case 2:
         b=float(input("enter base"))
         h=float(input("enter height"))
         print('area is ',0.5*b*h)
     case _:
         print('invalid option ')
      
      

#loops
#innitialization
i=1      
while i<=2:#ondition
    print("Clinton")
    i=i+1#updation
  
#even numbers from one to ten
#innitialization
i=2      
while i<=10:#ondition
    print(i)
    i=i+2#updation
  
#even odd from one to ten
#innitialization
i=1      
while i<=10:#ondition
   print(i)
   i=i+2#updation
     
#lab
#while loop
num=int(input("enter any number"))
s=0
while num!=0:
    r=num%10
    s=s+r
    num=num//10
    print("sum of digits is ",s)
   

#code factorial of a number
num=int(input("enter any number"))
fact=1
while num>0:
    fact=fact*num
    num=num-1
print("factorial is ",fact)
   

#For loop
#syntax2
#for variable in collection/iterable
    #statement1
    #statement2
#syntax2
#for variable in collection/iterable
    #statement1
    #statement2 
#else
    #statement3
    #statement4
 
 
#example
najjat="she makes cakes" 
for i in najjat :
    print(i)

str1=input("enter any word")
c=0
for ch in str1:
    if ch in "aeiouAEIOU":
        c+=1
        print('count of vowels ',c)        
#syntax
#lab
#range(stop) 1
#range(start,stop,step) 2
i=range(10)
for clint in i:
    print(clint)
    
#alphabet
for clint in range(65,91):
    print(chr(clint),end='  ')
print()
for clint in range(97,123):
    print(chr(clint),end='  ')
    


#27th april
#nested for
for row in range(1,4,1):
    for column in range(1,4,1):
       print(row, end=' ')
    print()    
    
#reverse order
for r in range(3,0,-1):
    for c in range(1,4,1):
        print(r,end=' ')
    print()
    
    
#reverse in column
for r in range(1,4,1):
    for c in range(3,0,-1):
        print(c,end=' ')
    print()
    
#nested while
choice="yes"
while choice!="no":
    num=int(input("enter any number"))
    i=1
    while i<=2:
        print(num,'*',i,'=',num*i)
        i=i+1
    choice=input("enter your choice")
    '''
    


#chapter3
#functions and modules
#funtion without argument and without return value
'''
    
def age():
    y=2026
    yb=int(input('enter year of birth'))
    z=y-yb
    print(z)
    
age()



#funtion with argument and without return value
def are(yb):
    y=2026
    z=y-yb
    print(z)
    
are(2000)
are(2002)


#funtion with argument and without return value
def add(y,b):
    
    z=y+b
    print(z)
    
add(1,2) 




#28th april
#funtion without argument and with return value
def add():
    num1=float(input("enter first number"))
    num2=float(input("enter second number"))
    return num1 + num2
def main():
    result = add()
    print("sum is ",result)
main()



#funtion with argument and with return value
def add(a,b):
    return a + b
def main():
    num1=float(input("enter first number"))
    num2=float(input("enter second number"))
    result = add(num1, num2)
    print("sum is ",result)
main()


#default or optional arguments
def fun1(a=2):
    c=a**a
    print(c)
fun1()
fun1(4)
    


#simple interest
def smi(p,t,r=1.4):
    s=(p*t*r)/100
    return s
def main():
    si=smi(9000,12,2.0)
    si2=smi(9000,14)
    print(f'simple interest is {si}')
    print(f'simple interest is {si2}')
    
main()


#variable length argument
def fun1(*a):
    print(a)
    print(type(a))
fun1(10)
fun1(100,200)
fun1(1,2,3,4,5,6,7)
fun1()


#29th april
#keyword argument
def fun(**a):
    print(a)
    #print(type(a))
fun(n1=10,n2=4)
fun()


#nested function
def funout():
    print('this is outer function')
    def funin():
        print('this is inner function')
    funin()
    print('function')
def main():    
  funout()
  print('this is inner function')
main()
print('this is function')
#lab book calculator

#local variable
def fun():
    a=3
    c=a**a
    print(c)
fun()

#global variables
a=3
c=a**a
def fun1():
    
    print(c)
fun1()
def fun1(a=2):
    
    print(c)
fun1()

#recursive functions
#finding factorial of a number
def factorial(n):
    if n==0:
        return 1
    else:
        return n*factorial(n-1)#funtion calling itself
def main():
    num=int(input("enter any number"))
    res=factorial(num)
    print(f'factorial is {res}')
main()
'''


#string
#can work with single, double and tripple quotes
#tripple quotes prints multiline strings
#single and double quotes print single line strings
#examples ...taken by clinton atulinde

'''
#6th may 2026
#reading a string
pretty='she is so beautiful'
#POSITIVE INDEXING starts from 0 while negative starts from negative 1
#for one charater

print(pretty[0])
print(pretty[1])
print(pretty[2])
print(pretty[3])
print(pretty[4])
print(pretty[5])
#slicing for multiple characters at a time
#0 is start point, 19-1 is the last index, 1 is the increment
print(pretty[0:19:1])
print(pretty[19:0:-1])
print(pretty[::-1])
print(pretty[-2:-7:-1])

#using for loop
for i in pretty:
    print(i)
    
#palindrom of a string(reverse of a string equal to original)
st=input('enter word')
if st[::-1]==st:
     print(st,' is palindrom')
else:
    print(st,' is not palindrom')

#functions in a string
pr='pin123#'
print(pr.capitalize())#capitalize first character
print(pr.find('p'))#find position of a character gives -1 if not found
print(pr.index('i'))#find index of a character gives error if not found
print(pr.isalnum())#if alpanumeric return true or false
print(pr.isalpha())#if alpha return true or false
print(pr.isdigit())#if digit return true or false
sw="Potton"
print(sw.islower())#if lower return true or false
print(sw.isupper())#if upper return true or false
print(sw.isspace())#if space return true or false
print(sw.istitle())#if title return true or false if 1st letter of each word is capital,true


#11th may
#collections
#-sequenced collections
##-list allows duplicates, different data types, same data types, mutable
ait=[10,23.5,'python']
print(ait)
print(type(ait))
#reading from a list
###indexing
print(ait[2])
print(ait[-1])
print(ait[0])
###slicing
print(ait[:3:])
print(ait[-1:4:-1])
###for loop
for i in ait:
    print(i)

##adding an item to the list
###append
ait=[]
a=ait.append(60)#adding 60 to the list. append only adds a single value to the list

#example2
n=int(input('enter number of player'))
score=[]
for i in range(n):
     a=int(input('enter score'))
     score.append(a)
print('the total score is',sum(score))
print('the minimum score is',min(score))
print('the maximum score is',max(score))

#updating elements
##using index
p=[10,20,30,40]#original elements
print(p)
p[0]=0#updating index 0 to value 0
print(p)

##using slicing
p[1:3:1]=[300,400]
print(p)

#deleting from a list
##using del
###using index
del p[0]
print(p)

###using slicing
del p[0:5:1]
print(p)

##using pop
###removing last element
p.pop()

##clear
p.clear()
print(p)

#lab program
stack=[]
while True:
    print('*****stack****')
    print('1.Push')#append
    print('2.Pop')#remove
    print('3.View')#view
    print('4.exit')#break
    opt=int(input('enter you option'))
    match(opt):
        case 1:
            ele=int(input('enter element to push'))
            stack.append(ele)
            print(ele, ' pushed to stack')
        case 2:
            if len(stack)==0:
                print('stack is empty')
            else:
                ele=stack.pop()
                print(ele,' is poped from stack')
        case 3:
            print('stack is ',stack)
        case 4:
            break
        case _:
            print('invalid option try again')




list1=[1,5,8,9,2,3,12,11,45,89,43,34,33,54,35]
even_list=[]
odd_list=[]
for value in list1:
    if value %2 == 0:
        even_list.append(value)
    else:
        odd_list.append(value)
print(even_list)
print(odd_list)

#13th may 2026
##dictionary
#its called map collection
#items are organised as key and value pair
#keys an not be modified and duplicated but can modify the values
d1={10:'john',20:'zack',30:'mimi'}
print(type(d1))
print(d1)
###acccessing data
####using key
print(d1[10])
#print(d1[40])#error becuse doesnt exist
####using loop
for i in d1:
    print(i,d1[i])
###modification using update method
d1.update({10:'salman',20:'thilak'})
print(d1)
####adding another item
d1.update({40:'clinton',50:'lawrence'})
print(d1)
#deleting a particular key
del d1[30]
print(d1)
#deleting the last item
d1.popitem()
print(d1)
#removing all the items
d1.clear()
print(d1)

#Nb:tuple is s1=(10,20)
#Nb:list is s1=[10,20]

try:
    num1=int(input('enter the first number'))
    num2=int(input('enter the second number'))

    c=num1/num2
    print(c)
except ZeroDivisionError:#divisor exception
    print('the number cannot be divided by zero')
except ValueError:#value error exception
    print('this is not the expected value, Clinton expected an integer value')
finally:
    print('powered by nextsolutech')

#pvm handles catch exceptions
#raise is handled for explicitly calling the except block 

#file handling
#syntax    filepointer=open("filenme","mode")
#modes in file handling, write:w,append:a, read:r
try:
    nt=input('write your story here')
         
    f=open("file1.txt","a")
    f.write(nt)
         
except OSError:
    print('error in creting file')
finally:
    f.close()
'''

'''
   
import os

FILE_NAME = "students.txt"

# Add a student
def add_student():
    roll = input("Enter Roll Number: ")
    name = input("Enter Name: ")
    grade = input("Enter Grade: ")

    with open(FILE_NAME, "a") as file:
        file.write(f"{roll},{name},{grade}\n")

    print("Student added successfully!\n")


# Delete a student by roll number
def delete_student():
    roll_to_delete = input("Enter Roll Number to delete: ")

    if not os.path.exists(FILE_NAME):
        print("No student records found.\n")
        return

    found = False
    updated_data = []

    with open(FILE_NAME, "r") as file:
        for line in file:
            roll, name, grade = line.strip().split(",")
            if roll != roll_to_delete:
                updated_data.append(line)
            else:
                found = True

    with open(FILE_NAME, "w") as file:
        file.writelines(updated_data)

    if found:
        print("Student deleted successfully!\n")
    else:
        print("Student not found!\n")


# Main program loop
def main():
    while True:
        print("=== Student Management System ===")
        print("1. Add Student")
        print("2. Delete Student")
        print("3. Exit")

        choice = input("Choose an option: ")

        if choice == "1":
            add_student()
        elif choice == "2":
            delete_student()
        elif choice == "3":
            print("Exiting program...")
            break
        else:
            print("Invalid choice! Try again.\n")


main()

import os
file_name = "studentsinfo.txt"
#  Add student
def add_student():
    roll = input("Enter Roll Number: ")
    name = input("Enter Name: ")
    grade = input("Enter Grade: ")

    # Open file in append mode (adds data at the end)
    with open(file_name, "a") as file:
        file.write(roll + "," + name + "," + grade + "\n")

    print("Student added successfully!\n")


#  Delete student
def delete_student():
    roll_to_delete = input("Enter Roll Number to delete: ")

    if not os.path.exists(file_name):
        print("No records found!\n")
        return

    found = False
    new_data = []

    # Read all students
    with open(file_name, "r") as file:
        for line in file:
            data = line.strip().split(",")

            # data = [roll, name, grade]
            if data[0] != roll_to_delete:
                new_data.append(line)
            else:
                found = True

    # Rewrite file without deleted student
    with open(file_name, "w") as file:
        file.writelines(new_data)

    if found:
        print("Student deleted successfully!\n")
    else:
        print("Student not found!\n")


# Main menu
def main():
    while True:
        print("===== Student Management System =====")
        print("1. Add Student")
        print("2. Delete Student")
        print("3. Exit")

        choice = input("Choose option: ")

        if choice == "1":
            add_student()
        elif choice == "2":
            delete_student()
        elif choice == "3":
            print("Goodbye")
            break
        else:
            print("Invalid choice, try again!\n")
# Program execution starts here
main()

# Input numbers
numbers = input("Enter numbers separated by spaces: ")

# Convert input into a list
numbers = numbers.split()

# Variables
sum = 0
positive = 0
negative = 0
zero = 0

# Loop through numbers
for n in numbers:
    num = int(n)

    # Positive, negative, or zero
    if num > 0:
        print(num, "is Positive")
        positive += 1
    elif num < 0:
        print(num, "is Negative")
        negative += 1
    else:
        print(num, "is Zero")
        zero += 1

    # Even or odd
    if num % 2 == 0:
        print(num, "is Even")
    else:
        print(num, "is Odd")

    # Add numbers
    sum += num

# Average
average = sum / len(numbers)

# Results
print("Sum =", sum)
print("Average =", average)

print("Positive numbers =", positive)
print("Negative numbers =", negative)
print("Zero numbers =", zero)


#18th may 2026
def main():
    n=input("enter what you know about clinton")
    try:
        f=open("trisha.txt","w")
        
        f.write(n)
    except Exception as e:
        print("error in creating file",e)
    finally:
       f.close()
main()

try:
    f = open("stud.txt","a")
    while True:
        roll=int(input("roll number"))
        name=input("name")
        course=input("course")
        print(roll, name,file=f)
        ch= input("add another student?").lower()
        if ch=="no":
            break
except Exception as e:
    print("unable to create file", e)
finally:
    f.close()

try:
    f = open("stud.txt","r")
    while True:
        stud=f.readline()
        if stud=="":
            break
        roll,name,course=stud.split()
        print(roll,name,course)
except Exception as e:
    print("file not found", e)
finally:
    if f:
        f.close()
        
        
        '''lab program
#read data from a file
import shutil
def read_from_file(filename):
    try:
        with open(filename, 'r') as file:
            content =file.read()
        print("file content read successfully:")
        print(content)
    except Exception as e:
        print(f"An error occurred: {e}")
        
#write data to file
def write_to_file(filename, data):
          try:
#   syntax: with open(filename,'mode') as file
            with open(filename,'w')as file:
                file.write(data)
            print(f"Data has been written to {filename}.")
          except Exception as e:
            print(f"An error occured: {e}")
       
#copy a file
def copy_file(source, destination):
    try:
        shutil.copy(source, destination)
        print(f"File copied from {source} to {destination}.")
    except Exception as e:
        print(f"An error occured: {e}")
        
write_to_file('example.txt', 'HELLO BSCAIT')
read_from_file('example.txt')
copy_file('example.txt', 'example_copy.txt')


import mysql.connector

try:
    # Connecting to MySQL
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="isbat2"
    )

    # Check connection
    if connection.is_connected():
        print("Connected to MySQL successfully")

except mysql.connector.Error as e:
    print("Error while connecting to MySQL:", e)

finally:
    # Closing connection
    if 'connection' in locals() and connection.is_connected():
        connection.close()
        print("MySQL connection closed")
   
#inserting
import mysql.connector

connection = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="isbat2"
)
c=connection.cursor()
while True:
    rollno=int(input('Rollno:'))
    name=(input('Name:'))
    sub1=int(input('Sub1:'))
    sub2=int(input('Sub2:'))
    sub3=int(input('Sub3:'))
    cmd="insert into student values(%s,%s,%s,%s,%s)"
    c.execute(cmd,params=(rollno,name,sub1,sub2,sub3))
    k=c.rowcount
    if k==1:
        print("student is added")
        connection.commit()
    ans=input("Add another student?").lower()
    if ans=="no":
        break
         


#read data
import mysql.connector

connection = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="isbat2"
)
c=connection.cursor()
c.execute("select * from student")
#display one student
stud1=c.fetchone()
print(stud1)
#fetch many records
stud2=c.fetchmany(2)
print(stud2)

#fetch all reords
stud3=c.fetchall()
print(stud3)


#25th
#update
import mysql.connector

connection = mysql.connector.connect(
host="localhost",
user="root",
password="",
database="isbat2"
)
c=connection.cursor()
while True:
    rollno=int(input('Rollno to update:'))
    name=(input('Name:'))
    sub1=int(input('Sub1:'))
    sub2=int(input('Sub2:'))
    sub3=int(input('Sub3:'))
    cmd="update student SET name=%s, sub1=%s, sub2=%s, sub3=%s WHERE rollno=%s"
    c.execute("update student SET name=%s, num1=%s, num2=%s, num3=%s WHERE rollno=%s",(name,sub1,sub2,sub3,rollno))
    k=c.rowcount
    if k>0:
        print("student record updated successfully")
        connection.commit()
    ans=input("update another student?").lower()
    if ans=="no":
        connection.close()
        break
         
import shutil

# 1. Read data from a file
def read_from_file(filename):
    try:
        with open(filename, 'r') as file:
            content = file.read()
        print("File content read successfully:")
        print(content)
    except FileNotFoundError:
        print(f"The file {filename} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# 2. Write data to a file
def write_to_file(filename, data):
    try:
        with open(filename, 'w') as file:
            file.write(data)
        print(f"Data has been written to {filename}.")
    except Exception as e:
        print(f"An error occurred: {e}")

# 3. Copy a file
def copy_file(source, destination):
    try:
        shutil.copy(source, destination)
        print(f"File copied from {source} to {destination}.")
    except FileNotFoundError:
        print(f"The source file {source} was not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

# Example usage

# Reading from a file
read_from_file('example.txt')

# Writing to a file
write_to_file('example.txt', 'This is a new line of text.')

# Copying a file
copy_file('example.txt', 'example_copy.txt')


import mysql.connector

cn=mysql.connector.connect(host="localhost",user="root",password="",database="isbat2")














import mysql.connector

try:
#establising connection
  conn=mysql.connector.connect(host='localhost',user='root', password='', database='cassiano')
#activating db
  cn=conn.cursor()
#prompting user
  rollno=int(input('enter your rollno '))
  name=input('enter your name ')
  password=input('enter your password ')
  age=int(input('enter your age '))
#sql command
  cmd="INSERT INTO student VALUES (%s,%s,%s,%s);"
#executing cmd
  cn.execute(cmd,(rollno,name,password,age,))
#saving changes
  conn.commit()
#closing connection
  conn.close()
except Exception as e:
    print('Error: ',e)
finally:
    print('bye bye')




'''
create table student if not exists (rollno int primary key auto_increment,
name varchar(20),
password varchar(20),
age int
)
name=input('Enter your name: ')
password=input('Enter your password: ')
Confirm_password=input('Re-enter your password: ')
if password==Confirm_password:
    if password.isalnum():
        if len(password)>=8:
            age=int(input('Enter your age: '))
            insert into student(name,password,age) values(name,password,age)
            print('Registration successful')
    
else:
    print('Password does not match')
      
'''


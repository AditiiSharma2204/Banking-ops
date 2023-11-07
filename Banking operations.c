#include<stdio.h>
#include<conio.h>
#include<string.h>
#include<stdlib.h>
#include<math.h>
char u[100],p[100],u1[100],p1[100];
int acc_no;
float balance,c_money,w_money,t_money,l_money;
void reg();
void login();
void menu();
void credit();
void loan();
void withdraw();
void transfer();
void home_loan();
void car_loan();
void personal_loan();
void logout();
main()
{
	reg();
}
void reg()
{
	printf("\t\vWelcome to registration\v\n");
	printf("To register a new user press ENTER\n");
	getch();
	system("cls");
	printf("Enter a username: ");
	gets(u);
	printf("Enter a password: ");
	gets(p);
	printf("Enter a 6 digit Account number: ");
	scanf("%d",&acc_no);
	printf("Enter the minimum balance you want to keep in the account %d: ",acc_no);
	scanf("%f",&balance);
	printf("Registration Successful\n");
	printf("Press ENTER to go to Login");
	getch();
	system("cls");
	login();
}
void login()
{
	printf("\t\vWelcome to Login\v");
	printf("To login enter your credentials\n");
	printf("USERNAME: ");
	scanf("%s",u1);
	printf("PASSWORD: ");
	scanf("%s",p1);
	int a=strcmp(u,u1);
	int b=strcmp(p,p1);
	if(a==0)
	{
		if(b==0)
		{
		printf("Login Successful\n");
		printf("Press ENTER");
		getch();
		system("cls");
		menu();
		}
		else
		{
		printf("Invalid Username or Password\n");
		printf("To go back to Login page press ENTER");
		getch();
		system("cls");
		login();
		}
	}
	else
	{
	printf("Invalid Username of Password\n");
	printf("To go back to Login page press ENTER");
	getch();
	system("cls");
	login();
	}
}
void menu()
{
	printf("\t\tAvailable balance: %.2f Rupees\t\tAccount number: %d\n",balance,acc_no);
	printf("Select the choice with which you want to proceed\n");
	printf("1. Credit money\n");
	printf("2. Withdraw money\n");
	printf("3. Transfer money\n");
	printf("4. Loans\n");
	printf("5. Logout\n");
	int choice;
	scanf("%d",&choice);
	switch(choice)
	{
		case 1: credit();
		break;
		case 2:
			withdraw();
			break;
		case 3: transfer();
		break;
		case 4:
			loan();
			break;
		case 5: system("cls");
		logout();
		break;
		default:
			{
			printf("Invalid choice\nPress ENTER to go back to menu");
			getch();
			menu();
			}
	}
}
void credit()
{
	system("cls");
	printf("Enter the amount to be credited: ");
	scanf("%f",&c_money);
	printf("Enter the account to be credited from: ");
	int acc;
	scanf("%d",&acc);
	printf("Enter the pin: ");
	int pin;
	scanf("%d",&pin);
	printf("Money added successfully\n");
	printf("Press ENTER to continue to menu");
	getch();
	system("cls");
	balance=balance+c_money;
	menu();
}
void loan()
{
	system("cls");
	int choice;
	printf("Enter the choice with which you want to proceed\n");
	printf("1.Home Loan\n2.Car Loan\n3.Personal Loan\n4.Back to Menu\n");
	scanf("%d",&choice);
	switch(choice)
	{
		case 1: home_loan();
		break;
		case 2: car_loan();
		break;
		case 3: personal_loan();
		break;
		case 4: system("cls");
		menu();
		break;
		default: printf("Invalid choice press ENTER to go back to choices\n");
		getch();
		system("cls");
		loan();
	}
}
void withdraw()
{
	system("cls");
	printf("Enter the amount to be debited: ");
	scanf("%f",&w_money);
	printf("Enter your pin: ");
	int pin;
	scanf("%d",&pin);
	printf("Amount successfully debited\n");
	balance=balance-w_money;
	printf("Press ENTER to go back to the menu");
	getch();
	system("cls");
	menu();
}
void transfer()
{
	system("cls");
	float tamt;
    int choice;
    printf("Enter the account number to transfer the money to: ");
    scanf("%f",&tamt);
    printf("Enter the amount to be transferred: ");
    scanf("%f",&t_money);
    balance=balance-t_money;
    printf("Select the mode of transfer:\n1-RTGS\n2-DD\n3-NEFT\n4-IMPS\n");
    scanf("%d",&choice);
    switch(choice)
    {
        case 1:
        printf("Enter the bank IFSC code of the receiver: ");
        int IFSC;
        scanf("%d",&IFSC);
        break;
        case 2:
        printf("Enter the payee name: ");
        char a[100];
        scanf("%s",a);
        printf("%s has received the funds\n",a);
        break;
        case 3:
        printf("Enter the bank IFSC code of the receiver: ");
        scanf("%d",&IFSC);
        break;
        case 4:
        printf("Enter the beneficiary MMID: ");
        int MMID;
        scanf("%d",&MMID);
        break;
        default:
        {
         printf("Enter a valid choice!\n");
         getch();
         system("cls");
         transfer();
        }
    }
    printf("%.2f has been successfully credited to account %.0f\n",t_money,tamt);
    printf("Press ENTER to go back to menu");
    getch();
    system("cls");
    menu();
}
void home_loan()
{
	printf("Enter the loan amount: ");
	scanf("%f",&l_money);
	printf("Enter the value of assets (COLLATERAL) that you own: ");
	float asset;
	scanf("%f",&asset);
	if(l_money<asset)
	{
		printf("Enter the purpose of taking the loan: ");
		char purp[800];
		gets(purp);
		char reason[600];
		gets(reason);
		if(l_money<2000000)
		{
			printf("The time period of the loan is 4 years\n");
			char b='%';
			printf("The rate of interest is 8.6 %c per anunum\n",b);
			float rate=8.6;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
		else if(2000000<=l_money<6000000)
		{
			printf("The time period of the loan is 6 years\n");
			char b='%';
			printf("The rate of interest is 9.1 %c per anunum\n",b);
			float rate=9.1;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
		else if(l_money>=6000000)
		{
			printf("The time period of the loan is 8 years\n");
			char b='%';
			printf("The rate of interest is 9.5 %c per anunum\n",b);
			float rate=9.5;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
	}
	else
	{
		printf("You do not qualify for a home loan\n");
		getch();
		system("cls");
		menu();
	}
}
void personal_loan()
{
	printf("Enter the loan amount: ");
	scanf("%f",&l_money);
	printf("Enter the value of assets (COLLATERAL) that you own: ");
	float asset;
	scanf("%f",&asset);
	if(l_money<asset)
	{
		printf("Enter the purpose of taking the loan: ");
		char purp[800];
		gets(purp);
		char reason[600];
		gets(reason);
		if(l_money<2000000)
		{
			printf("The time period of the loan is 4 years\n");
			char b='%';
			printf("The rate of interest is 8.6 %c per anunum\n",b);
			float rate=8.6;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
		else if(2000000<=l_money<6000000)
		{
			printf("The time period of the loan is 6 years\n");
			char b='%';
			printf("The rate of interest is 9.1 %c per anunum\n",b);
			float rate=9.1;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
		else if(l_money>=6000000)
		{
			printf("The time period of the loan is 8 years\n");
			char b='%';
			printf("The rate of interest is 9.5 %c per anunum\n",b);
			float rate=9.5;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
	}
	else
	{
		printf("You do not qualify for a personal loan\n");
		getch();
		system("cls");
		menu();
	}
}
void car_loan()
{
	printf("Enter the loan amount: ");
	scanf("%f",&l_money);
	printf("Enter the value of assets (COLLATERAL) that you own: ");
	float asset;
	scanf("%f",&asset);
	if(l_money<asset)
	{
		printf("Enter the purpose of taking the loan: ");
		char purp[800];
		gets(purp);
		char reason[600];
		gets(reason);
		if(l_money<2000000)
		{
			printf("The time period of the loan is 4 years\n");
			char b='%';
			printf("The rate of interest is 8.6 %c per anunum\n",b);
			float rate=8.6;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
		else if(2000000<=l_money<6000000)
		{
			printf("The time period of the loan is 6 years\n");
			char b='%';
			printf("The rate of interest is 9.1 %c per anunum\n",b);
			float rate=9.1;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
		else if(l_money>=6000000)
		{
			printf("The time period of the loan is 8 years\n");
			char b='%';
			printf("The rate of interest is 9.5 %c per anunum\n",b);
			float rate=9.5;
			float interest=(l_money*rate)/(float)100;
			printf("Interest amount per year: %.2f\n",interest);
			printf("LOAN APPROVED!!\n");
			balance=balance+l_money;
			printf("To go back to the menu press ENTER\n");
			getch();
			system("cls");
			menu();
		}
	}
	else
	{
		printf("You do not qualify for a car loan\n");
		getch();
		system("cls");
		menu();
	}
}
void logout()
{
	int choice;
	printf("1. Login\n2. Registration\n3. Exit Application\n");
	scanf("%d",&choice);
	switch(choice)
	{
		case 1: login();
		system("cls");
		break;
		case 2: reg();
		system("cls");
		break;
		case 3: exit(0);
		system("cls");
		break;
		default:
		{ 
		printf("Invalid choice\nPress ENTER");
		getch();
		system("cls");
		logout();
		}
	}
}

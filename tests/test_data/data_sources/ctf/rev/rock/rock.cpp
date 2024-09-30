#include <string>
#include <iostream>
#include <algorithm>
#include <fstream>

using namespace std;

class DarkTemplar{

public:
	virtual int getSerial() = 0;
	


};


class HighTemplar: public DarkTemplar{
public:
	HighTemplar(const string& solution) : solution(solution),rock_flag(solution){}

	void calculate(){
		if (solution.length() != 30){
			cout << "Too short or too long" << endl;
			exit(-1);
		}


		
		for(int i =0;i <= solution.length();i++){
				solution[i] = char((solution[i]^0x50)+(20%25));

		}	
		
		for(int i =0; i <= solution.length();i++){
				solution[i] = char((solution[i] ^ 0x10)+(265%999));
		}
	
	}

	int getSerial(){
		for(int i = 0;i< solution.length();i++){
			if (answer[i] == solution[i]){
				cout << "Pass " << i  << endl;	
			}else{
				cout << "You did not pass " << i << endl;
				flag = 1;
				break;
			}
				
		}
		
		return flag;

	}

	string getFlag(){
	
		return rock_flag;
	
	}

private:
	int value;
	int flag = 0;
	string solution;
	string rock_flag;
	string answer = "FLAG23456912365453475897834567";


};

struct Node{
public:
	Node(const char& character) : str(character){}

	char str;
	Node* prev;
	Node *next;

};


void func3(string prevent,int i){
	if (prevent[i] != '\0'){
		prevent[i] = char((prevent[i] ^ 0x20)+35); 
		i += 1;
		func3(prevent,i);
	}else{
		return;
	}
	
}

string func2(string prevent){
	
	for(int i = 0;i < prevent.length();i++){

		prevent[i] = char((prevent[i] ^ 0x50)+(50%25));
	}

	return prevent;	
	
}


string func1(string prevent){

	Node * root = new Node('R');
	Node * tmp = root;
	string payload;

	for(int i = 0; i < prevent.length();i++){
		tmp->next = new Node(prevent[i]);
		tmp = tmp->next;
	}
	

	while(root->next != nullptr){
		root = root->next;
		payload += root->str;

	}
	
	return payload;

}

int main(){
	string prevent;
	int val = 0;

	cin >> prevent;
	
	cout << "-------------------------------------------" << endl;
	cout << "Quote from people's champ" << endl;	
	cout << "-------------------------------------------" << endl;
	cout << "*My goal was never to be the loudest or the craziest. It was to be the most entertaining." << endl;
	cout << "*Wrestling was like stand-up comedy for me." << endl;
	cout << "*I like to use the hard times in the past to motivate me today." << endl;
	cout << "-------------------------------------------" << endl;

	HighTemplar high(prevent);
	cout << "Checking...." << endl;

	func3(func2(func1(prevent)),val);
	
	high.calculate();

	if(!(high.getSerial())){
	
	
		cout << "/////////////////////////////////" << endl;
		cout << "Do not be angry. Happy Hacking :)" << endl;
		cout << "/////////////////////////////////" << endl;
		
		cout << "Flag{" << high.getFlag() << "}" << endl;


	}
		
	
		


	return 0;
}

#include <string>
#include <iostream>

using namespace std;

int main(){
	string solution = "FLAG23456912365453475897834567";
	for(int i =0; i <= solution.length();i++){
        cout << i << " " << solution[i] << " " << ((int) solution[i]);
		solution[i] = char(((solution[i]-(265%999))^0x10));
        cout << " " << solution[i] << " " << ((int) solution[i]) << endl;
	} 	

	for(int j =0; j <= solution.length();j++){
        cout << j << " " << solution[j] << " " << ((int) solution[j]);
		solution[j] = char((solution[j] - 20)^0x50);
        cout << " " << solution[j] << " " << ((int) solution[j]) << endl;
	}

	cout << "FLAG:" << solution << endl;



}

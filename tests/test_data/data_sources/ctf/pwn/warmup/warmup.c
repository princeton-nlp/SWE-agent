#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>
#include <signal.h>
#include <unistd.h>

void easy(){

	system("cat flag.txt");

}

int main(){
	char buffer[50];
	write(1,"-Warm Up-\n",10);
	char address[50];
	write(1,"WOW:",4);
	sprintf(address,"%p\n",easy);
	write(1,address,9);
	write(1,">",1);
	gets(buffer);


}

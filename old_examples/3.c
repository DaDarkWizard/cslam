/*Oliver Johnson
Weston Moelker
Zach Michelson
Birch Olsen
Sequencing
ojjohnso@mtu.edu
wlmoelke@mtu.edu
zrmichel@mtu.edu
mrolsen@mtu.edu
9/20/2024
*/
#include <stdio.h>

int main(void)
{
    int a;
    int b;
    int n;
    int k=1;
    int q=0;
    //ask user for input
    printf("Give a, b, and n: ");
    scanf("%d %d %d", &a, &b, &n);

    printf(" %d",a);
    //run until k is equal not less than n
    while(k<n)
    {
        //temp variable q to hold the preous value of a
        q=a;
        //set a equal to b
        a=b;
        //add a and q to make a new b
        b=a+q;
        //output a
        printf(" %d",a);
        k++;
    }
    printf("\n");
}


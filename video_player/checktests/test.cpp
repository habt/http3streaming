#include <bits/stdc++.h>
using namespace std;
  
int main()
{
    deque<std::string> dq = { "one", "two", "three" };
    cout << "original:";
    deque<string>::iterator it;

    for (it = dq.begin(); it != dq.end(); ++it)
        cout << ' ' << *it;
    cout << '\n'; 
    
    vector<std::string> vc = {"ten"};
    dq.clear();
    it = dq.insert(dq.end(), vc.begin(), vc.end()); // 1 10 2 3 4 5
  
    std::cout << "Deque contains:";
    for (it = dq.begin(); it != dq.end(); ++it)
        cout << ' ' << *it;
    cout << '\n';
   
    vc.clear();
    vc.push_back("four");
    dq.pop_front();
    it = dq.insert(dq.end(), vc.begin(), vc.end());
    std::cout << "redoing after pop\n";

    std::cout << "New Deque contains:";
    for (it = dq.begin(); it != dq.end(); ++it)
        cout << ' ' << *it;
    cout << '\n';
  
    return 0;
}

### 一、前置数学知识（主要是贝叶斯公式）
####贝叶斯公式   ![image](https://img2024.cnblogs.com/blog/3249866/202601/3249866-20260119145150769-1919260283.png)
      正向为全概率公式：P(A)=P(A|B1)*P(B1)+P(A|B2)*P(B2)+P(A|B3)*P(B3)+...+P(A|Bn)*P(Bn)
      逆向为贝叶斯：A已经发生的情况下，求是由Bi引起的概率有多大 P（Bi|A）=P(ABi)/P(A)=P(A|Bi)*P(Bi)/ sum(P(A|Bk)*P(Bk))
####马尔科夫链
    一个状态序列S,其中状态si的取值仅由s(i-1)取值决定，而与再之前的状态无关
####马尔科夫平稳状态：在大量满足马尔科夫链的实例顺序中，各个状态的发生频率是收敛的，用一个行向量$\pi$来表示。
* pi的代数计算：
![image](https://img2024.cnblogs.com/blog/3249866/202601/3249866-20260119160603009-1088857407.png)

```
#include<iostream>
using namespace std;
#include<random>

int main()
{
    char st1='A',st2='B',st3='C';
    double n1=0,n2=0,n3=0;
    char temp='A';
    int timess=0;
    cin>>timess;
    for(int i=0;i<timess;i++)
    {
        random_device rd;
        mt19937 gen(rd());
        uniform_int_distribution<int> dist(1,100);
        int random_num = dist(gen);
      if(temp=='A'&&random_num<=20)
      {
            n1++;
            temp='A';
      }
      else if(temp=='A'&&random_num>20&&random_num<=80)
      {
            n2++;
            temp='B';
      }
      else if(temp=='A'&&random_num>80&&random_num<=100)
      {
            n3++;
            temp='C';
      }
      else if(temp=='B'&&random_num<=30)
      {
            n1++;
            temp='A';
      }
      else if(temp=='B'&&random_num>30&&random_num<=100)
      {
            n3++;
            temp='C';
      }
      else if(temp=='C'&&random_num<=50)
      {
            n3++;
            temp='C';
      }
      else if (temp=='C'&&random_num>=50)
      {
            n1++;
            temp='A';
      }
      cout<<temp<<" ";
    }
    cout<<endl;
    cout<<"N1:"<<n1/timess<<endl;
    cout<<"N2:"<<n2/timess<<endl;
    cout<<"N3:"<<n3/timess<<endl;
    return 0;
    
}
```
收敛结果为：
![image](https://img2024.cnblogs.com/blog/3249866/202601/3249866-20260119160629705-22702816.png)

* pi的理论计算：转移矩阵特征值为1的特征向量。(不断迭代到不动点pi*A=pi相当于是特征值为1的特征向量)

### 二、基本概念
---
#### 状态：
       无法观察的状态集合P（p1,p2,...,pn）
       可观察到状态集合Q(q1,q2,...,qm).
#### 转移矩阵：
       无法观察的状态P内部转移概率矩阵A A的意义：aij代表从状态pi——>pj的概率；
       无法观察状态P导致可观察状态Q转移概率矩阵B B的意义：bij代表pi条件下qj发生的概率
#### 快速记忆的例子：![image](https://img2024.cnblogs.com/blog/3249866/202601/3249866-20260119144155404-4796036.png)
#### 核心用法：
*     由可观察的状态序列求不可观察到的状态序列（由已知状态得到未知状态），由于具有不确定性，实际上相当于一个极大似然估计。
  在数学上而言求的是：给定可观察状态序列Y发生情况下，不可观察状态序列X发生的概率P（X|Y）,再由贝叶斯定理=P(Y|X)*P(X)/P(Y),而由于P(Y)确定，所以只需要求最大的P(Y|X)*P(X)=P(X,Y)也就是两个状态的联合概率分布；
  而又由于马尔科夫链的性质，本状态取值仅仅取决于前一个状态的取值故有
![image](https://img2024.cnblogs.com/blog/3249866/202601/3249866-20260119163925571-1887599737.png)
![image](https://img2024.cnblogs.com/blog/3249866/202601/3249866-20260119170527524-1287266847.png)
*    ##### 前向算法：
    必要性：由于一个已知的可观测序列对应的可能的不可观测序列的种类呈指数级上升，因此全部计算较为复杂。
    技巧：由于有重复计算部分而导致复杂度高，因此可以使用 **动态规划**来简化复杂度
*    ####后向算法
*    ####维特比算法
*    ####Baum-Welch算法

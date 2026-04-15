#1

def sum_array(array):
    total = 0           

    for num in array:
        total += num   

    return total      


array = [1, 4, 6, 9, -2, 8]
print(sum_array(array))

"""
Time Complexity : O(n)
    We iterate through each element in the array exactly once.
    As the array grows by n elements, the work grows linearly.

Space Complexity: O(1)
    Only one extra variable (total) is used,
    regardless of how large the input array is.
"""

#AI Prompts: 
# Explain what this means: the time complexity of your solution using Big O notation

#2 

def second_largest(array):
    
    if len(array) < 2:
        return None

    largest = float('-inf')         
    second = float('-inf')          

    for num in array:              
        if num > largest:          
            second = largest        
            largest = num           
        elif num > second and num != largest:  
            second = num           

    if second == float('-inf'):   
        return None

    return second 
arr = [6, 9, 12, -4, 3, 2, 9]
print("Second largest: ",(second_largest(arr)))                 

"""
linear time, which is optimal. You can't find the second largest without looking at every element at least once.
"""

#AI prompt: how would you go about finding th esecond largest value using an if statement

#3

def difference(dif_array):

    large = float('-inf')
    small = float('inf')   

    for num in dif_array:
        if num < small:    
            small = num    
        if num > large:    
            large = num    

    return large - small  


dif_array = [6, 9, 12, -4, 3, 2, 9]
print("Difference of Max and Min in the array:", difference(dif_array))

"""
linear time, which is optimal. You can't find the largest and smallest values without looking at every element at least once.
"""

#AI Prompt: What is wrong with this code:
"""

Deleting a node from a Binary Search Tree is tricky because unlike inserting or searching, you have to think about what happens to the rest of the tree after the node is gone.
If the node has no children you can just remove it, no problem. 
If it has one child, you simply promote that child up into its place. 
The hard case is when the node has two children — you can't just rip it out without disconnecting the tree.
The trick is to find the smallest value in the right subtree, swap it into the deleted node's spot, then remove that value from the right subtree instead. 
It sounds roundabout but it's a neat solution that keeps the tree intact.
There are also a few things to be careful of. Trying to delete from an empty tree, or deleting a value that doesn't exist, should just do nothing rather than crash. 
Deleting the root node works fine but you need to make sure your code updates the root reference afterward, otherwise you'll lose track of the whole tree. 
Duplicate values are another headache — you need to decide upfront whether you want to delete just one copy or all of them. 
Overall it's the kind of problem that seems complicated at first but makes a lot of sense once you see the pattern.

"""
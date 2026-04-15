
class TreeNode:
    def __init__(self, val=0):
        self.left = None
        self.right = None
        self.val = val

def insert(root, val):
    if not root:
        return TreeNode(val)
    if val < root.val:
        root.left = insert(root.left, val)
    elif val > root.val:
        root.right = insert(root.right, val)
    return root



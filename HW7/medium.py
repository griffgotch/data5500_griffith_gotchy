def search(root, val):
    if not root:
        return False
    if val == root.val:
        return True
    if val < root.val:
        return search(root.left, val)
    return search(root.right, val)

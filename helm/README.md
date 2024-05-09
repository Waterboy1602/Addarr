### Helm Chart for addarr

Required: Storage Class

Edit the values in values.yaml and install with:

```
helm upgrade -i addarr . -f values.yaml
```

or into namespace:

```
helm upgrade -i --namespace addarr --create-namespace addarr . -f values.yaml
```

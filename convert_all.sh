#!/usr/bin/env bash

OLD=tests/registries/ledger-asset-dapps
NEW=tests/registries/clear-signing-erc7730-registry

find $old -name eip712.json | while read in_file; do
  in_dir=$(dirname $in_file)
  dapp=$(basename $in_dir)
  network=$(basename $(dirname $in_dir))
  out_dir=$NEW/registry/$dapp
  mkdir -p $out_dir
  out_file=$out_dir/eip712-$dapp-$network.json
  pdm run erc7730 convert eip712-to-erc7730 $in_file $out_file
done

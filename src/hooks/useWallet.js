import { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserProvider } from 'ethers';
import { CHAIN_ID, CHAIN_ID_HEX, NETWORK_NAME } from '../constants';

export function useWallet() {
  const [provider, setProvider] = useState(null);
  const [signer, setSigner] = useState(null);
  const [address, setAddress] = useState(null);
  const [isConnected, setIsConnected] = useState(false);
  const [wrongNetwork, setWrongNetwork] = useState(false);
  const [chainId, setChainId] = useState(null);
  const [walletError, setWalletError] = useState('');

  const chainChangedRef = useRef(null);
  const accountsChangedRef = useRef(null);

  const clearError = useCallback(() => {
    setWalletError('');
  }, []);

  const removeListeners = useCallback(() => {
    if (!window.ethereum) return;
    if (chainChangedRef.current) {
      window.ethereum.removeListener('chainChanged', chainChangedRef.current);
      chainChangedRef.current = null;
    }
    if (accountsChangedRef.current) {
      window.ethereum.removeListener('accountsChanged', accountsChangedRef.current);
      accountsChangedRef.current = null;
    }
  }, []);

  const disconnect = useCallback(() => {
    removeListeners();
    setProvider(null);
    setSigner(null);
    setAddress(null);
    setIsConnected(false);
    setWrongNetwork(false);
    setChainId(null);
    setWalletError('');
  }, [removeListeners]);

  const connect = useCallback(async () => {
    clearError();

    if (!window.ethereum) {
      setWalletError('No wallet detected. Install MetaMask or a compatible wallet.');
      return;
    }

    try {
      const accounts = await window.ethereum.request({ method: 'eth_requestAccounts' });
      if (!accounts || accounts.length === 0) {
        throw new Error('No accounts returned');
      }

      const currentChainId = await window.ethereum.request({ method: 'eth_chainId' });

      if (parseInt(currentChainId, 16) !== CHAIN_ID) {
        try {
          await window.ethereum.request({
            method: 'wallet_switchEthereumChain',
            params: [{ chainId: CHAIN_ID_HEX }]
          });
        } catch (switchError) {
          if (switchError?.code === 4902) {
            await window.ethereum.request({
              method: 'wallet_addEthereumChain',
              params: [
                {
                  chainId: CHAIN_ID_HEX,
                  chainName: NETWORK_NAME,
                  nativeCurrency: {
                    name: 'GEN',
                    symbol: 'GEN',
                    decimals: 18
                  },
                  rpcUrls: ['http://127.0.0.1:4000/api']
                }
              ]
            });
          } else {
            setWalletError('Switch to GenLayer Studio network to continue.');
            setWrongNetwork(true);
            return;
          }
        }
      }

      const nextProvider = new BrowserProvider(window.ethereum);
      const nextSigner = await nextProvider.getSigner();
      const nextAddress = await nextSigner.getAddress();
      const confirmedNetwork = await nextProvider.getNetwork();

      if (Number(confirmedNetwork.chainId) !== CHAIN_ID) {
        setWalletError('Wrong network. GenLayer Studio (61999) required.');
        setWrongNetwork(true);
        return;
      }

      const handleChainChanged = () => {
        window.location.reload();
      };

      const handleAccountsChanged = (nextAccounts) => {
        if (!nextAccounts || nextAccounts.length === 0) {
          disconnect();
        } else {
          const newProvider = new BrowserProvider(window.ethereum);
          newProvider.getSigner().then((newSigner) => {
            setProvider(newProvider);
            setSigner(newSigner);
            setAddress(nextAccounts[0]);
          });
        }
      };

      removeListeners();
      chainChangedRef.current = handleChainChanged;
      accountsChangedRef.current = handleAccountsChanged;
      window.ethereum.on('chainChanged', handleChainChanged);
      window.ethereum.on('accountsChanged', handleAccountsChanged);

      setProvider(nextProvider);
      setSigner(nextSigner);
      setAddress(nextAddress);
      setChainId(Number(confirmedNetwork.chainId));
      setWrongNetwork(false);
      setIsConnected(true);
      setWalletError('');
    } catch (error) {
      if (error?.code === 4001) {
        setWalletError('Switch to GenLayer Studio network to continue.');
      } else {
        setWalletError(error?.message || 'Failed to connect wallet');
      }
      setWrongNetwork(true);
    }
  }, [clearError, disconnect, removeListeners]);

  const switchToGenLayer = useCallback(async () => {
    await connect();
  }, [connect]);

  useEffect(() => {
    return () => {
      removeListeners();
    };
  }, [removeListeners]);

  return {
    provider,
    signer,
    address,
    isConnected,
    wrongNetwork,
    chainId,
    walletError,
    connect,
    disconnect,
    switchToGenLayer,
    clearError
  };
}

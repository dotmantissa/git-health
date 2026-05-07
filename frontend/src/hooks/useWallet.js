import { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserProvider } from 'ethers';
import { CHAIN_ID, CHAIN_ID_HEX, NETWORK_NAME, RPC_URL } from '../constants';

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

  const disconnect = useCallback(() => {
    if (window.ethereum && chainChangedRef.current && accountsChangedRef.current) {
      window.ethereum.removeListener('chainChanged', chainChangedRef.current);
      window.ethereum.removeListener('accountsChanged', accountsChangedRef.current);
    }

    setProvider(null);
    setSigner(null);
    setAddress(null);
    setIsConnected(false);
    setWrongNetwork(false);
    setChainId(null);
    setWalletError('');
  }, []);

  const ensureCorrectNetwork = useCallback(async () => {
    try {
      await window.ethereum.request({
        method: 'wallet_switchEthereumChain',
        params: [{ chainId: CHAIN_ID_HEX }]
      });
      setWrongNetwork(false);
      return true;
    } catch (switchError) {
      if (switchError?.code === 4902) {
        try {
          await window.ethereum.request({
            method: 'wallet_addEthereumChain',
            params: [
              {
                chainId: CHAIN_ID_HEX,
                chainName: NETWORK_NAME,
                nativeCurrency: { name: 'GEN', symbol: 'GEN', decimals: 18 },
                rpcUrls: [RPC_URL]
              }
            ]
          });
          setWrongNetwork(false);
          return true;
        } catch (addError) {
          if (addError?.code === 4001) {
            setWrongNetwork(true);
            setWalletError('Wrong network. Switch to GenLayer Studio to continue.');
            return false;
          }
          throw addError;
        }
      }

      if (switchError?.code === 4001) {
        setWrongNetwork(true);
        setWalletError('Wrong network. Switch to GenLayer Studio to continue.');
        return false;
      }

      throw switchError;
    }
  }, []);

  const connect = useCallback(async () => {
    clearError();

    if (!window.ethereum) {
      setWalletError('No wallet detected. Install MetaMask or a compatible wallet.');
      return;
    }

    try {
      await window.ethereum.request({ method: 'eth_requestAccounts' });

      const browserProvider = new BrowserProvider(window.ethereum);
      const network = await browserProvider.getNetwork();
      const currentChainId = Number(network.chainId);

      if (currentChainId !== CHAIN_ID) {
        const switched = await ensureCorrectNetwork();
        if (!switched) {
          return;
        }
      }

      const freshProvider = new BrowserProvider(window.ethereum);
      const freshNetwork = await freshProvider.getNetwork();
      const finalChainId = Number(freshNetwork.chainId);

      if (finalChainId !== CHAIN_ID) {
        setWrongNetwork(true);
        setWalletError('Wrong network. Switch to GenLayer Studio to continue.');
        return;
      }

      const freshSigner = await freshProvider.getSigner();
      const signerAddress = await freshSigner.getAddress();

      setProvider(freshProvider);
      setSigner(freshSigner);
      setAddress(signerAddress);
      setChainId(finalChainId);
      setWrongNetwork(false);
      setIsConnected(true);

      const onChainChanged = () => {
        window.location.reload();
      };

      const onAccountsChanged = async (accounts) => {
        if (!accounts || accounts.length === 0) {
          disconnect();
          return;
        }

        const updatedProvider = new BrowserProvider(window.ethereum);
        const updatedNetwork = await updatedProvider.getNetwork();
        const updatedChainId = Number(updatedNetwork.chainId);
        const updatedSigner = await updatedProvider.getSigner();

        setProvider(updatedProvider);
        setSigner(updatedSigner);
        setAddress(accounts[0]);
        setChainId(updatedChainId);
        setWrongNetwork(updatedChainId !== CHAIN_ID);
      };

      chainChangedRef.current = onChainChanged;
      accountsChangedRef.current = onAccountsChanged;

      window.ethereum.on('chainChanged', onChainChanged);
      window.ethereum.on('accountsChanged', onAccountsChanged);
    } catch (error) {
      setWalletError(error?.message || 'Failed to connect wallet');
    }
  }, [clearError, disconnect, ensureCorrectNetwork]);

  const switchToGenLayer = useCallback(async () => {
    clearError();
    try {
      const success = await ensureCorrectNetwork();
      if (success && isConnected) {
        const refreshedProvider = new BrowserProvider(window.ethereum);
        const refreshedNetwork = await refreshedProvider.getNetwork();
        const refreshedChainId = Number(refreshedNetwork.chainId);
        const refreshedSigner = await refreshedProvider.getSigner();
        const refreshedAddress = await refreshedSigner.getAddress();

        setProvider(refreshedProvider);
        setSigner(refreshedSigner);
        setAddress(refreshedAddress);
        setChainId(refreshedChainId);
        setWrongNetwork(false);
      }
    } catch (error) {
      setWalletError(error?.message || 'Failed to switch network');
    }
  }, [clearError, ensureCorrectNetwork, isConnected]);

  useEffect(() => {
    return () => {
      if (window.ethereum && chainChangedRef.current && accountsChangedRef.current) {
        window.ethereum.removeListener('chainChanged', chainChangedRef.current);
        window.ethereum.removeListener('accountsChanged', accountsChangedRef.current);
      }
    };
  }, []);

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

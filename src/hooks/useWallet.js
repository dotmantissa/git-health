import { useCallback, useEffect, useRef, useState } from 'react';
import { BrowserProvider } from 'ethers';
import { CHAIN_ID, CHAIN_ID_HEX, NETWORK_NAME, RPC_URL } from '../constants';

const WALLET_SESSION_KEY = 'githealth_wallet_connected';

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
    }
    if (accountsChangedRef.current) {
      window.ethereum.removeListener('accountsChanged', accountsChangedRef.current);
    }
    chainChangedRef.current = null;
    accountsChangedRef.current = null;
  }, []);

  const disconnect = useCallback(() => {
    removeListeners();
    localStorage.removeItem(WALLET_SESSION_KEY);

    setProvider(null);
    setSigner(null);
    setAddress(null);
    setIsConnected(false);
    setWrongNetwork(false);
    setChainId(null);
    setWalletError('');
  }, [removeListeners]);

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

  const attachListeners = useCallback(
    (onDisconnect) => {
      if (!window.ethereum) return;
      removeListeners();

      const onChainChanged = () => {
        window.location.reload();
      };

      const onAccountsChanged = async (accounts) => {
        if (!accounts || accounts.length === 0) {
          onDisconnect();
          return;
        }

        try {
          const updatedProvider = new BrowserProvider(window.ethereum);
          const updatedNetwork = await updatedProvider.getNetwork();
          const updatedChainId = Number(updatedNetwork.chainId);
          const updatedSigner = await updatedProvider.getSigner();
          const updatedAddress = await updatedSigner.getAddress();

          setProvider(updatedProvider);
          setSigner(updatedSigner);
          setAddress(updatedAddress);
          setChainId(updatedChainId);
          setWrongNetwork(updatedChainId !== CHAIN_ID);
          setIsConnected(true);
        } catch (error) {
          setWalletError(error?.message || 'Failed to update wallet account');
        }
      };

      chainChangedRef.current = onChainChanged;
      accountsChangedRef.current = onAccountsChanged;
      window.ethereum.on('chainChanged', onChainChanged);
      window.ethereum.on('accountsChanged', onAccountsChanged);
    },
    [removeListeners]
  );

  const connectWithMode = useCallback(async (silent = false) => {
    clearError();

    if (!window.ethereum) {
      if (!silent) {
        setWalletError('No wallet detected. Install MetaMask or a compatible wallet.');
      }
      return;
    }

    try {
      const accounts = await window.ethereum.request({
        method: silent ? 'eth_accounts' : 'eth_requestAccounts'
      });
      if (!accounts || accounts.length === 0) {
        if (!silent) {
          setWalletError('No account connected in wallet.');
        }
        disconnect();
        return;
      }

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
        if (!silent) {
          setWalletError('Wrong network. Switch to GenLayer Studio to continue.');
        }
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
      localStorage.setItem(WALLET_SESSION_KEY, '1');
      attachListeners(disconnect);
    } catch (error) {
      if (!silent) {
        setWalletError(error?.message || 'Failed to connect wallet');
      }
    }
  }, [attachListeners, clearError, disconnect, ensureCorrectNetwork]);

  const connect = useCallback(async () => {
    await connectWithMode(false);
  }, [connectWithMode]);

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
        setIsConnected(true);
      }
    } catch (error) {
      setWalletError(error?.message || 'Failed to switch network');
    }
  }, [clearError, ensureCorrectNetwork, isConnected]);

  useEffect(() => {
    const shouldRestore = localStorage.getItem(WALLET_SESSION_KEY) === '1';
    if (shouldRestore) {
      connectWithMode(true);
    }

    return () => {
      removeListeners();
    };
  }, [connectWithMode, removeListeners]);

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

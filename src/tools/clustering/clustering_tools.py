import numpy as np
import pandas as pd
import os
from typing import Dict, Any
from sklearn.cluster import KMeans, DBSCAN
from sklearn.preprocessing import StandardScaler
from sklearn.mixture import BayesianGaussianMixture

from tools.data_loading.data_loading_utils import _load_data_from_file


def register_clustering_tools(mcp):
    """Register clustering tools for the given MCP server instance"""

    @mcp.tool()
    def kmeans_clustering(file_path: str, n_clusters: int = 3, random_state: int = 42) -> Dict[str, Any]:
        """
        Perform K-means clustering on data from a file.

        K-means is a centroid-based clustering algorithm that partitions data into k clusters.

        PROS:
        - Computationally efficient: O(n*k*i) where n=samples, k=clusters, i=iterations
        - Simple and well-understood algorithm
        - Works well with spherical, well-separated clusters
        - Guaranteed convergence
        - Good performance on large datasets
        - Produces compact, balanced clusters

        CONS:
        - Requires pre-specifying number of clusters (k)
        - Sensitive to the random initialization of cluster centers
        - Assumes spherical clusters of similar size
        - Sensitive to outliers (outliers can skew centroids)
        - Struggles with non-convex cluster shapes
        - Poor performance on clusters with different densities

        BEST USE CASES:
        - When you know the approximate number of clusters
        - Data with spherical, well-separated clusters
        - Large datasets where efficiency is important
        - When clusters are of similar size and density
        - As a preprocessing step for other algorithms using a k number larger than the actual

        AVOID WHEN:
        - Clusters have very different sizes or densities
        - Data contains many outliers
        - Clusters have non-spherical shapes
        - Number of clusters is completely unknown

        Args:
            file_path: Path to CSV file containing the dataset
            n_clusters: Number of clusters to find
            random_state: Random seed for reproducibility

        Returns:
            Dictionary with cluster labels, centroids, and algorithm metadata
        """
        try:
            data_array = _load_data_from_file(file_path)
            
            # Standardize the data for better clustering
            scaler = StandardScaler()
            data_scaled = scaler.fit_transform(data_array)
            
            # Perform K-means clustering
            kmeans = KMeans(n_clusters=n_clusters, random_state=random_state, n_init=10)
            labels = kmeans.fit_predict(data_scaled)
            
            # Transform centroids back to original scale
            centroids_scaled = kmeans.cluster_centers_
            centroids = scaler.inverse_transform(centroids_scaled)
            
            # Calculate inertia (within-cluster sum of squares)
            inertia = kmeans.inertia_
            
            # Calculate cluster statistics
            unique_labels = np.unique(labels)
            cluster_stats = {}
            for label in unique_labels:
                cluster_points = data_array[labels == label]
                cluster_stats[int(label)] = {
                    "size": len(cluster_points),
                    "centroid": centroids[label].tolist(),
                    "std_x": float(cluster_points[:, 0].std()),
                    "std_y": float(cluster_points[:, 1].std())
                }
            
            # Create reports directory if it doesn't exist
            os.makedirs('reports', exist_ok=True)
            
            # Save results to CSV file to prevent context overflow
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            results_file = f"reports/{base_name}_kmeans_results.csv"
            
            # Create results DataFrame
            results_df = pd.DataFrame({
                'point_id': range(len(labels)),
                'cluster_label': labels,
                'x': data_array[:, 0],
                'y': data_array[:, 1],
                'source_file': file_path,
                'algorithm': 'K-means'
            })
            
            results_df.to_csv(results_file, index=False)
            
            # Save metadata separately
            metadata_file = results_file.replace('.csv', '_metadata.txt')
            with open(metadata_file, 'w') as f:
                f.write(f"Algorithm: K-means\n")
                f.write(f"Source file: {file_path}\n")
                f.write(f"Number of clusters: {n_clusters}\n")
                f.write(f"Inertia: {inertia:.4f}\n")
                f.write(f"Algorithm complexity: O(n*k*i)\n")
                f.write(f"Efficiency: High\n")
                f.write(f"Scalability: Excellent\n")
                f.write(f"Outlier sensitivity: High\n")
                f.write(f"Cluster sizes: {[cluster_stats[i]['size'] for i in range(n_clusters)]}\n")
                for i in range(n_clusters):
                    f.write(f"Cluster {i}: size={cluster_stats[i]['size']}, centroid={cluster_stats[i]['centroid']}\n")
            
            return {
                "success": True,
                "algorithm": "K-means",
                "source_file": file_path,
                "results_file": os.path.abspath(results_file),
                "n_clusters": n_clusters,
                "inertia": float(inertia),
                "file_size_bytes": os.path.getsize(results_file),
                "message": f"K-means clustering completed. Results saved to {results_file}",
                "summary": {
                    "clusters_found": n_clusters,
                    "cluster_sizes": [cluster_stats[i]["size"] for i in range(n_clusters)],
                    "efficiency": "High"
                }
            }
        except Exception as e:
            return {"error": f"K-means clustering failed: {str(e)}"}

    @mcp.tool()
    def dbscan(file_path: str, eps: float = 0.5, min_samples: int = 5) -> Dict[str, Any]:
        """
        Perform DBSCAN clustering on data from a file.

        DBSCAN (Density-Based Spatial Clustering of Applications with Noise) is a density-based clustering algorithm that groups together points 
        that are closely packed together, marking points that lie alone in low-density regions as outliers.

        PROS:
        - Does not require pre-specifying number of clusters
        - Can find arbitrarily shaped clusters
        - Robust to outliers and noise
        - Can handle clusters of varying densities

        CONS:
        - Sensitive to parameter selection (eps and min_samples)
        - Struggles with high-dimensional data
        - Computationally intensive for large datasets (O(n log n) to O(n^2))
        - May produce different results with different parameter settings

        BEST USE CASES:
        - When the number of clusters is unknown
        - Data with noise and outliers
        - Clusters with irregular shapes
        - Datasets with varying cluster densities

        AVOID WHEN:
        - Data is high-dimensional
        - Clusters are of similar size and density
        - When computational efficiency is a primary concern
        
        Args:
            file_path: Path to CSV file containing the dataset
            eps: Maximum distance between two samples for one to be considered as in the neighborhood of the other
            min_samples: Minimum number of samples in a neighborhood for a point to be considered as a core point
        
        Returns:
            Dictionary with cluster labels, outliers, and algorithm metadata

            
        """
        try:
            data_array = _load_data_from_file(file_path)
            
            # Standardize the data
            scaler = StandardScaler()
            data_scaled = scaler.fit_transform(data_array)
            
            # Perform DBSCAN clustering
            dbscan = DBSCAN(eps=eps, min_samples=min_samples)
            labels = dbscan.fit_predict(data_scaled)
            
            # Identify outliers (label = -1)
            outlier_mask = labels == -1
            outliers = data_array[outlier_mask]
            
            # Get unique cluster labels (excluding -1 for noise)
            unique_labels = np.unique(labels[labels != -1])
            n_clusters = len(unique_labels)
            
            # Calculate cluster statistics
            cluster_stats = {}
            for label in unique_labels:
                cluster_points = data_array[labels == label]
                cluster_stats[int(label)] = {
                    "size": len(cluster_points),
                    "center": cluster_points.mean(axis=0).tolist(),
                    "std_x": float(cluster_points[:, 0].std()),
                    "std_y": float(cluster_points[:, 1].std())
                }
            
            # Create reports directory if it doesn't exist
            os.makedirs('reports', exist_ok=True)
            
            # Save results to CSV file to prevent context overflow
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            results_file = f"reports/{base_name}_dbscan_results.csv"
            
            # Create results DataFrame
            results_df = pd.DataFrame({
                'point_id': range(len(labels)),
                'cluster_label': labels,
                'x': data_array[:, 0],
                'y': data_array[:, 1],
                'source_file': file_path,
                'algorithm': 'DBSCAN'
            })
            
            results_df.to_csv(results_file, index=False)
            
            # Save metadata separately
            metadata_file = results_file.replace('.csv', '_metadata.txt')
            with open(metadata_file, 'w') as f:
                f.write(f"Algorithm: DBSCAN\n")
                f.write(f"Source file: {file_path}\n")
                f.write(f"Number of clusters: {n_clusters}\n")
                f.write(f"Number of outliers: {np.sum(outlier_mask)}\n")
                f.write(f"Cluster label for outliers: {-1}\n")
                f.write(f"Outliers: {outliers}")
                f.write(f"Parameters: eps={eps}, min_samples={min_samples}\n")
                f.write(f"Algorithm complexity: O(n log n)\n")
                f.write(f"Efficiency: Medium\n")
                f.write(f"Scalability: Good\n")
                f.write(f"Outlier sensitivity: Low (robust)\n")
                if n_clusters > 0:
                    cluster_sizes = [cluster_stats[i]['size'] for i in range(n_clusters)]
                    f.write(f"Cluster sizes: {cluster_sizes}\n")
                    for i in range(n_clusters):
                        f.write(f"Cluster {i}: size={cluster_stats[i]['size']}, center={cluster_stats[i]['center']}\n")
            
            return {
                "success": True,
                "algorithm": "DBSCAN",
                "source_file": file_path,
                "results_file": os.path.abspath(results_file),
                "n_clusters": int(n_clusters),
                "n_outliers": int(np.sum(outlier_mask)),
                "file_size_bytes": os.path.getsize(results_file),
                "parameters": {"eps": eps, "min_samples": min_samples},
                "message": f"DBSCAN clustering completed. Results saved to {results_file}",
                "summary": {
                    "clusters_found": int(n_clusters),
                    "outliers_detected": int(np.sum(outlier_mask)),
                    "efficiency": "Medium"
                }
            }
        except Exception as e:
            return {"error": f"DBSCAN clustering failed: {str(e)}"}

    @mcp.tool()
    def bayesian_gaussian_mixture(file_path: str, n_components: int = 3, covariance_type: str = 'full',
                                  weight_concentration_prior_type: str = 'dirichlet_process',
                                  random_state: int = 42) -> Dict[str, Any]:
        """
        Perform Bayesian Gaussian Mixture clustering on data from a file.

        Uses `sklearn.mixture.BayesianGaussianMixture` which provides a probabilistic mixture
        model with automatic complexity selection via a Dirichlet process prior.

        PROS:
        - Can infer effective number of components
        - Probabilistic assignments (soft clustering)
        - Robust to over-specifying `n_components`

        CONS:
        - More computationally expensive than K-means
        - Requires careful prior/parameter choices for some datasets

        BEST USE CASES:
        - When the true number of clusters is unknown and the model should infer complexity
        - When soft (probabilistic) cluster assignments are required
        - Datasets with overlapping clusters or varying cluster sizes/densities
        - When you may over-specify `n_components` and want the model to prune unused components
        - As a generative/density model for sampling or anomaly scoring

        AVOID WHEN:
        - Working with very large datasets where runtime and memory are constrained
        - High-dimensional data without prior dimensionality reduction
        - You need extremely fast, deterministic hard-centroid clustering (use K-means)
        - You cannot or do not want to tune priors or spend time validating model selection
        - When data contains strong density variations or noise that may mislead the mixture model

        Args:
            file_path: Path to CSV file containing the dataset
            n_components: Maximum number of mixture components to consider
            covariance_type: Type of covariance ('full', 'tied', 'diag', 'spherical')
            weight_concentration_prior_type: 'dirichlet_process' or 'dirichlet_distribution'
            random_state: Random seed for reproducibility

        Returns:
            Dictionary with clustering results, metadata, and saved result file path
        """
        try:
            data_array = _load_data_from_file(file_path)

            # Standardize the data
            scaler = StandardScaler()
            data_scaled = scaler.fit_transform(data_array)

            # Fit Bayesian Gaussian Mixture
            bgm = BayesianGaussianMixture(
                n_components=n_components,
                covariance_type=covariance_type,
                weight_concentration_prior_type=weight_concentration_prior_type,
                random_state=random_state
            )
            bgm.fit(data_scaled)

            # Hard labels via MAP assignment
            labels = bgm.predict(data_scaled)

            # Soft assignment probabilities
            probs = bgm.predict_proba(data_scaled)
            max_probs = probs.max(axis=1)

            # Effective components (weights above small threshold)
            effective_components = int((bgm.weights_ > 1e-3).sum())

            # Transform component means back to original scale
            means_scaled = bgm.means_
            try:
                means = scaler.inverse_transform(means_scaled)
            except Exception:
                means = means_scaled

            # Create reports directory and save results
            os.makedirs('reports', exist_ok=True)
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            results_file = f"reports/{base_name}_bayesian_gmm_results.csv"

            results_df = pd.DataFrame({
                'point_id': range(len(labels)),
                'cluster_label': labels,
                'x': data_array[:, 0],
                'y': data_array[:, 1],
                'max_probability': max_probs,
                'source_file': file_path,
                'algorithm': 'BayesianGaussianMixture'
            })

            results_df.to_csv(results_file, index=False)

            # Save metadata
            metadata_file = results_file.replace('.csv', '_metadata.txt')
            with open(metadata_file, 'w') as f:
                f.write(f"Algorithm: BayesianGaussianMixture\n")
                f.write(f"Source file: {file_path}\n")
                f.write(f"Requested components: {n_components}\n")
                f.write(f"Effective components: {effective_components}\n")
                f.write(f"Covariance type: {covariance_type}\n")
                f.write(f"Weight concentration prior type: {weight_concentration_prior_type}\n")
                f.write(f"Converged: {getattr(bgm, 'converged_', 'Unknown')}\n")
                f.write(f"Weights: {bgm.weights_.tolist()}\n")
                f.write(f"Means (original scale): {means.tolist()}\n")

            return {
                "success": True,
                "algorithm": "BayesianGaussianMixture",
                "source_file": file_path,
                "results_file": os.path.abspath(results_file),
                "n_components_requested": n_components,
                "effective_components": effective_components,
                "file_size_bytes": os.path.getsize(results_file),
                "message": f"Bayesian GMM clustering completed. Results saved to {results_file}",
                "summary": {
                    "clusters_found": effective_components,
                    "soft_assignments": True
                }
            }
        except Exception as e:
            return {"error": f"Bayesian GMM clustering failed: {str(e)}"}

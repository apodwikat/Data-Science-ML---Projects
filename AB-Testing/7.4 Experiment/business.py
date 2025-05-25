import math
import numpy as np
from datetime import datetime, timedelta
import pandas as pd
import plotly.express as px
import scipy
from database import DFRepository  # Changed from MongoRepository
from statsmodels.stats.contingency_tables import Table2x2
from statsmodels.stats.power import GofChisquarePower
# from teaching_tools.ab_test.experiment import Experiment

# Default DataFrame loading function



def get_default_df():
    return pd.read_excel(r"C:\Users\hp\WorldQuantum\7) A-B Testing\Wq-TestInfo-AB.xlsx")

class GraphBuilder:
    """Methods for building Graphs."""

    def __init__(self, repo=None):
        """init

        Parameters
        ----------
        repo : DFRepository, optional
            Data source
        """
        if repo is None:
            df = get_default_df()
            self.repo = DFRepository(df)
        else:
            self.repo = repo

    def build_nat_choropleth(self):
        """Creates nationality choropleth map."""
        df_nationality = self.repo.get_nationality_value_counts(normalize=True)
        fig = px.choropleth(
            data_frame=df_nationality,
            locations="country_iso3",
            color="count_pct",
            projection="natural earth",
            color_continuous_scale=px.colors.sequential.Oranges,
            title="DS Applicants: Nationality"
        )
        return fig

    def build_age_hist(self):

        """Create age histogram.

        Returns
        -------
        Figure
        """
        # Get ages from respository
        ages = self.repo.get_ages()
        # Create Figure
        fig = px.histogram(x=ages, nbins=20, title="DS Applicants: Distribution of Ages")
        # Set axis labels
        fig.update_layout(xaxis_title="Age", yaxis_title="Frequency [count]")
        # Return Figure
        return fig

    def build_ed_bar(self):

        """Creates education level bar chart.

        Returns
        -------
        Figure
        """
        # Get education level value counts from repo
        education = self.repo.get_ed_value_counts(normalize=True)
        # Create Figure
        fig = px.bar(
        x=education,
        y=education.index,
        orientation="h",
        title="DS Applicants: Highest Degree Earned"
        )
        # Add axis labels
        fig.update_layout(xaxis_title="Frequency [count]", yaxis_title="Degree")
        # Return Figure
        return fig

    def build_contingency_bar(self):
        """Creates side-by-side bar chart from contingency table."""
        try:
            # Get contingency table data from repo
            data = self.repo.get_contingency_table()

            if not data.empty:
                # Print data for debugging
                print("Contingency table data:")
                print(data)

                # Convert the contingency table to a format suitable for plotly
                df_melted = data.reset_index().melt(
                    id_vars='group',
                    var_name='admissionsQuiz',
                    value_name='count'
                )

                print("Melted data:")
                print(df_melted)

                # Create Figure
                fig = px.bar(
                    data_frame=df_melted,
                    x='group',
                    y='count',
                    color='admissionsQuiz',
                    barmode="group",
                    title="Admissions Quiz Completion by Group",
                    labels={
                        'group': 'Group',
                        'count': 'Number of Applicants',
                        'admissionsQuiz': 'Quiz Status'
                    }
                )

                # Update layout
                fig.update_layout(
                    xaxis_title="Group",
                    yaxis_title="Number of Applicants",
                    legend_title="Quiz Status",
                    showlegend=True
                )

                return fig
            else:
                # Create an empty figure with a message
                fig = px.bar(
                    title="No experiment data available",
                    labels={'x': 'Group', 'y': 'Count'}
                )
                fig.add_annotation(
                    text="No data available - Run the experiment first",
                    xref="paper", yref="paper",
                    x=0.5, y=0.5,
                    showarrow=False
                )
                return fig

        except Exception as e:
            print(f"Error in build_contingency_bar: {e}")
            # Create an error figure
            fig = px.bar(
                title="Error creating plot",
                labels={'x': 'Group', 'y': 'Count'}
            )
            fig.add_annotation(
                text=f"Error: {str(e)}",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False
            )
            return fig

class Experiment:
    def __init__(self, df):
        self.df = df.copy()
        print("Experiment initialized with DataFrame shape:", self.df.shape)

    def reset_experiment(self):
        """Reset any experiment-related columns"""
        if 'group' in self.df.columns:
            self.df.drop('group', axis=1, inplace=True)
            print("Group column reset")

    def run_experiment(self, days):
        """Run the experiment for specified number of days"""
        try:
            print(f"Running experiment for {days} days")

            # Filter data for specified days
            start_date = self.df['createdAt'].min()
            end_date = start_date + pd.Timedelta(days=days)
            mask = self.df['createdAt'].between(start_date, end_date)
            experiment_data = self.df[mask].copy()

            print(f"Filtered data shape: {experiment_data.shape}")

            # Randomly assign groups with correct names
            experiment_data['group'] = np.random.choice(
                ['no email (control)', 'email (treatment)'],
                size=len(experiment_data)
            )

            print("Groups assigned")
            print("Unique groups:", experiment_data['group'].unique())

            # Update the main DataFrame with the experimental data
            self.df.loc[mask, 'group'] = experiment_data['group']

            print("Main DataFrame updated")
            print("Final group counts:", self.df['group'].value_counts())

            return experiment_data
        except Exception as e:
            print(f"Error in run_experiment: {e}")
            return None

class StatsBuilder:
    """Methods for statistical analysis."""

    def __init__(self, repo=None):
        """init

        Parameters
        ----------
        repo : DFRepository, optional
            Data source
        """
        if repo is None:
            df = get_default_df()
            self.repo = DFRepository(df)
        else:
            self.repo = repo

    def calculate_n_obs(self, effect_size):
        """Calculate the number of observations needed to detect effect size.

        Parameters
        ----------
        effect_size : float
            Effect size you want to be able to detect

        Returns
        -------
        int
            Total number of observations needed, across two experimental groups.
        """
        # Calculate group size, w/ alpha=0.05 and power=0.8
        chi_square_power = GofChisquarePower()
        group_size = math.ceil(
            chi_square_power.solve_power(effect_size=effect_size, alpha=0.05, power=0.80)
        )
        # Return number of observations (group size * 2)
        return group_size * 2

    def calculate_cdf_pct(self, n_obs, days):
        """Calculate percent chance of gathering specified observations."""
        daily_counts = self.repo.get_no_quiz_per_day()

        mean_daily = daily_counts.mean()
        std_daily = daily_counts.std()

        mean_days = mean_daily * days
        std_days = std_daily * np.sqrt(days)

        prob = 1 - scipy.stats.norm.cdf(n_obs, mean_days, std_days)
        # Turn probability to percentage
        pct = prob * 100
        # Return percentage
        return pct

    def run_experiment(self, days):
        """Run experiment. Add results to repository."""
        try:
            print(f"Running experiment for {days} days")

            # Instantiate Experiment
            exp = Experiment(self.repo.df)
            print("Experiment instance created")

            # Reset experiment
            exp.reset_experiment()
            print("Experiment reset")

            # Run Experiment
            result = exp.run_experiment(days=days)
            print("Experiment run completed")

            # Update repository DataFrame
            self.repo.df = exp.df

            print("DataFrame updated")
            print("Group values after experiment:", self.repo.df['group'].unique())

            return result
        except Exception as e:
            print(f"Error in run_experiment: {e}")
            return None

    def run_chi_square(self):
        """Tests nominal association."""
        try:
            # Get data from repo
            data = self.repo.get_contingency_table()

            if not data.empty and data.shape == (2, 2):
                # Create `Table2X2` from data
                contingency_table = Table2x2(data.values)

                # Run chi-square test
                chi_square_test = contingency_table.test_nominal_association()

                return chi_square_test
            return None
        except Exception as e:
            print(f"Error in run_chi_square: {e}")
            return None
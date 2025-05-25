# database.py
import pandas as pd
from country_converter import CountryConverter
from datetime import datetime, timedelta

class DFRepository:
    """For interacting with DataFrame."""

    def __init__(self, df):
        """init

        Parameters
        ----------
        df : pd.DataFrame
            DataFrame containing the applicant data
        """
        self.df = df

    def get_nationality_value_counts(self, normalize=True):
        """Return nationality value counts.

        Parameters
        ----------
        normalize : bool, optional
            Whether to normalize frequency counts, by default True

        Returns
        -------
        pd.DataFrame
            Results with columns: 'count', 'country_name', 'country_iso2', 'country_iso3'
        """
        # Get result from DataFrame
        value_counts = self.df['countryISO2'].value_counts()
        df_nationality = pd.DataFrame({
            'country_iso2': value_counts.index,
            'count': value_counts.values
        }).sort_values('count')

        # Add country names and ISO3
        cc = CountryConverter()
        df_nationality["country_name"] = cc.convert(
            df_nationality["country_iso2"], to="name_short"
        )
        df_nationality["country_iso3"] = cc.convert(
            df_nationality["country_iso2"], to="ISO3"
        )

        # Transform frequency count to pct
        if normalize:
            df_nationality["count_pct"] = (
                    (df_nationality["count"] / df_nationality["count"].sum()) * 100
            )

        return df_nationality

    def get_ages(self):
        """Gets applicants ages from DataFrame.

        Returns
        -------
        pd.Series
            Series of integer ages
        """
        today = pd.Timestamp('now')
        birthdays = pd.to_datetime(self.df['birthday'])
        ages = ((today - birthdays).dt.days / 365.25).astype(int)

        return ages

    def __ed_sort(self, counts):
        """Helper function for self.get_ed_value_counts."""
        degrees = [
            "High School or Baccalaureate",
            "Some College (1-3 years)",
            "Bachelor's degree",
            "Master's degree",
            "Doctorate (e.g. PhD)",
        ]
        mapping = {k: v for v, k in enumerate(degrees)}
        sort_order = [mapping.get(c, len(degrees)) for c in counts]  # Handle missing degrees
        return sort_order

    def get_ed_value_counts(self, normalize=False):
        """Gets value counts of applicant education levels.

        Parameters
        ----------
        normalize : bool, optional
            Whether or not to return normalized value counts, by default False

        Returns
        -------
        pd.Series
            W/ index sorted by education level
        """
        # Get degree value counts from DataFrame (similar to MongoDB aggregation)
        value_counts = self.df['highestDegreeEarned'].value_counts()

        # Create DataFrame similar to MongoDB result
        result_df = pd.DataFrame({
            'highest_degree_earned': value_counts.index,
            'count': value_counts.values
        })

        # Load result into DataFrame and set index (matching MongoDB version)
        education = (
            result_df
                .rename(columns={"highest_degree_earned": "highest_degree_earned"})
                .set_index("highest_degree_earned")
        )

        # Ensure it's a Series
        education = education["count"]

        # Sort Series using `self.__ed_sort`
        education = education.sort_index(key=self.__ed_sort)

        # Optional: Normalize Series
        if normalize:
            education = (education / education.sum()) * 100

        # Return Series
        return education

    def get_no_quiz_per_day(self):
        """Calculates number of no-quiz applicants per day."""
        # Convert createdAt to datetime
        self.df['createdAt'] = pd.to_datetime(self.df['createdAt'])

        # Filter incomplete quizzes and group by date
        incomplete = self.df[self.df['admissionsQuiz'] == 'incomplete']
        daily_counts = (
            incomplete.groupby(incomplete['createdAt'].dt.date)
                .size()
                .sort_index()
                .rename('new_users')
        )

        return daily_counts

    def get_contingency_table(self):
        """Creates crosstab of experimental groups by quiz completion."""
        try:
            if 'group' in self.df.columns:
                print("Group column exists")
                print("Unique groups:", self.df['group'].unique())

                if set(['group', 'admissionsQuiz']).issubset(self.df.columns):
                    print("Both columns exist")
                    # Remove any rows where either group or admissionsQuiz is null
                    valid_data = self.df.dropna(subset=['group', 'admissionsQuiz'])

                    print("Valid data shape:", valid_data.shape)
                    print("Unique groups in valid data:", valid_data['group'].unique())
                    print("Unique quiz status:", valid_data['admissionsQuiz'].unique())

                    if not valid_data.empty:
                        contingency = pd.crosstab(
                            index=valid_data['group'],
                            columns=valid_data['admissionsQuiz']
                        )
                        print("Contingency table:")
                        print(contingency)
                        return contingency
                    else:
                        print("Valid data is empty")
                else:
                    print("Missing required columns")
            else:
                print("No group column found")
            return pd.DataFrame()
        except Exception as e:
            print(f"Error in get_contingency_table: {e}")
            return pd.DataFrame()
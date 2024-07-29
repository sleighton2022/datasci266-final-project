# -*- coding: utf-8 -*-
"""summary_utils

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1FbpmVB0KnQhTDj-WRALB1_qByGzwJVke
"""

#summary_utils.py

from rouge_score import rouge_scorer
from nltk.translate.bleu_score import sentence_bleu, SmoothingFunction
from datasets import Dataset
from datasets import load_dataset
import pandas as pd
import bert_score
from sentence_transformers import SentenceTransformer, util
import google.generativeai as genai
from google.generativeai import GenerativeModel
from google.colab import userdata
from transformers import pipeline

#############################################################################
#############################################################################
### SummaryEvalutator
#############################################################################
#############################################################################

class SummaryEvaluator:
    """
    A class for evaluating text summarization models using ROUGE and BLEU metrics.
    """

    def __init__(self, rouge_metrics=['rouge1', 'rouge2', 'rougeL'], use_stemmer=True,
                 bert_model="bert-base-uncased", sentence_transformer_model="all-mpnet-base-v2"):
        """
        Initializes the RougeBleuEvaluator.

        Args:
            rouge_metrics (list): List of ROUGE metrics to calculate (e.g., ['rouge1', 'rouge2', 'rougeL']).
            use_stemmer (bool): Whether to use stemming for calculating ROUGE scores.
        """
        self.rouge_scorer = rouge_scorer.RougeScorer(rouge_metrics, use_stemmer=use_stemmer)
        self.smoothing_function = SmoothingFunction().method4  # Choose a smoothing method
        self.rouge_metrics = rouge_metrics
        self.bert_model = bert_model
        self.sentence_transformer = SentenceTransformer(sentence_transformer_model)

    def calculate_rouge(self, reference_summaries, generated_summaries):
        """
        Calculates ROUGE scores.
        """
        if isinstance(reference_summaries, Dataset):
            reference_summaries = reference_summaries["summary"]

        rouge_scores = []
        for ref_summary, gen_summary in zip(reference_summaries, generated_summaries):
            scores = self.rouge_scorer.score(ref_summary, gen_summary)
            rouge_scores.append(scores)

        avg_rouge_scores = {
            metric: sum(score[metric].fmeasure for score in rouge_scores) / len(rouge_scores)
            for metric in self.rouge_metrics
        }

        return avg_rouge_scores

    def calculate_bleu(self, reference_summaries, generated_summaries):
        """
        Calculates BLEU scores.
        """

        if isinstance(reference_summaries, Dataset):
            reference_summaries = reference_summaries["summary"]

        bleu_scores = []
        for ref_summary, gen_summary in zip(reference_summaries, generated_summaries):
            # Tokenize summaries into words or subwords (depends on your model)
            reference_tokens = ref_summary.split()
            generated_tokens = gen_summary.split()
            score = sentence_bleu([reference_tokens], generated_tokens, smoothing_function=self.smoothing_function)
            bleu_scores.append(score)

        avg_bleu_score = sum(bleu_scores) / len(bleu_scores)

        return avg_bleu_score

    def calculate_bertscore(self, reference_summaries, generated_summaries):
        """
        Calculates BERTScore (F1) for a set of reference and generated summaries.
        """

        if isinstance(reference_summaries, Dataset):
            reference_summaries = reference_summaries["summary"]

        with warnings.catch_warnings():
            # Suppress specific warnings here
            warnings.filterwarnings('ignore', message=".*contains 'beta'.*")
            warnings.filterwarnings('ignore', category=UserWarning)

        _, _, bert_scores = bert_score.score(
            generated_summaries, reference_summaries, model_type=self.bert_model,
            lang="en", verbose=False
        )

        avg_bert_score = bert_scores.mean().item()  # Average F1 score
        return avg_bert_score

    def calculate_vector_similarity(self, reference_summaries, generated_summaries):
        """
        Calculates cosine similarity between reference and generated summary embeddings.
        """

        if isinstance(reference_summaries, Dataset):
            reference_summaries = reference_summaries["summary"]

        ref_embeddings = self.sentence_transformer.encode(reference_summaries, convert_to_tensor=True)
        gen_embeddings = self.sentence_transformer.encode(generated_summaries, convert_to_tensor=True)
        cosine_scores = util.cos_sim(ref_embeddings, gen_embeddings)

        avg_similarity = cosine_scores.diagonal().mean().item()  # Average cosine similarity
        return avg_similarity

    def evaluate(self, reference_summaries, generated_summaries, metrics=None):
        """
        Calculates and prints specified evaluation scores.

        Args:
            reference_summaries (list or Dataset): Reference summaries (gold standard).
            generated_summaries (list): Generated summaries (from the model).
            metrics (list, optional): List of metrics to calculate. If None, all available
                                     metrics are calculated (default is None).
        Returns:
            dict: A dictionary containing the average scores for the specified metrics.
        """

        all_metrics = {
            "rouge": self.calculate_rouge,
            "bleu": self.calculate_bleu,
            "bertscore": self.calculate_bertscore,
            "vector_similarity": self.calculate_vector_similarity,
        }

        # If no metrics specified, calculate all
        if metrics is None:
            metrics = all_metrics.keys()

        results = {}
        for metric in metrics:
            if metric in all_metrics:
                results[metric] = all_metrics[metric](reference_summaries, generated_summaries)
                print(f"Average {metric.upper()} score:", results[metric])
            else:
                print(f"Unknown metric: {metric}")

        return results


#############################################################################
#############################################################################
### DatasetManager
#############################################################################
#############################################################################

class DatasetManager:
    """
    A class for loading and sampling datasets from the Hugging Face Datasets library.
    """

    def __init__(self, dataset_name="xsum", sample_size=1, seed=42,):
        """
        Initializes the DatasetManager.

        Args:
            dataset_name (str): Name of the dataset to load (default is "xsum").
            sample_size (int): Number of examples to sample (default is 1).
            seed (int): Seed for shuffling the dataset (default is 42).
        """
        self.dataset_name = dataset_name
        self.sample_size = sample_size
        self.seed = seed
        self._dataset = None  # Initialize dataset attribute

    def util_load_dataset(self):
        """
        Loads the full dataset and stores it as an attribute.
        """
        if self._dataset is None:
            self._dataset = load_dataset(self.dataset_name)
        return self._dataset

    def load_sampled_dataset(self,dataset_label="train"):
        """
        Loads and samples a subset of the dataset.
        """
        dataset = self.util_load_dataset()  # Ensure the full dataset is loaded
        return dataset[dataset_label].shuffle(seed=self.seed).select(range(self.sample_size))

    # Additional methods for convenience (optional)
    def get_dataset_name(self):
        """
        Returns the name of the loaded dataset.
        """
        return self.dataset_name

    def get_sample_size(self):
        """
        Returns the current sample size.
        """
        return self.sample_size

    def set_sample_size(self, new_size):
        """
        Updates the sample size.
        """
        self.sample_size = new_size

    def get_seed(self):
        """
        Returns the current seed.
        """
        return self.seed

    def set_seed(self, new_seed):
        """
        Updates the seed.
        """
        self.seed = new_seed

    def explore_dataset(self):
        """
        Explores the dataset and prints the first few rows.
        """
        dataset = self.load_dataset()  # Ensure the full dataset is loaded

        train_df = pd.DataFrame(dataset['train'])
        validation_df = pd.DataFrame(dataset['validation'])
        test_df = pd.DataFrame(dataset['test'])

        print("Number of Training Examples:", len(train_df))
        print("Number of Validation Examples:", len(validation_df))
        print("Number of Test Examples:", len(test_df))

    def print_train_dataset_head(self,dataset_label="train"):
        """
        Prints information about the loaded dataset.
        """
        dataset = self.load_dataset()  # Ensure the full dataset is loaded
        train_df = pd.DataFrame(dataset[dataset_label])
        print(train_df.head().to_markdown(index=False, numalign="left", stralign="left")) # Show first 5 rows of the training set in a markdown table

#############################################################################
#############################################################################
### SummaryModel
#############################################################################
#############################################################################

class SummaryModel:
    """
    A class for evaluating and generating summaries using a model with flexible prompts.
    """

    def __init__(self, model, tokenizer, max_position_embeddings=512, max_length=150, min_length=30,
                 length_penalty=2.0, num_beams=4, early_stopping=True):
        """
        Initializes the SummarizationModel.

        Args:
            model: The T5 model for summarization (e.g., T5ForConditionalGeneration).
            tokenizer: The T5 tokenizer for preprocessing.
            max_length (int): Maximum length of the generated summary.
            min_length (int): Minimum length of the generated summary.
            length_penalty (float): Penalty for summary length.
            num_beams (int): Number of beams for beam search decoding.
            early_stopping (bool): Whether to use early stopping in beam search.
        """

        self.max_length = max_length
        self.min_length = min_length
        self.length_penalty = length_penalty
        self.num_beams = num_beams
        self.early_stopping = early_stopping
        self.max_position_embeddings = max_position_embeddings
        self.model = model
        self.tokenizer = tokenizer

    def default_prompt(self,prompt_template,document):
        """
        Returns the default prompt.
        """
        return prompt_template.format(document=document)

    def default_summarizer(self,prompt):
        """
        Returns the default summarizer.
        """
        device = 0 if torch.cuda.is_available() else -1
        self.summarizer = pipeline("summarization", model=self.model, tokenizer=self.tokenizer, device=device)
        return self.summarizer(
                prompt,
                max_length=self.max_length,
                min_length=self.min_length,
                length_penalty=self.length_penalty,
                num_beams=self.num_beams,
                early_stopping=self.early_stopping
            )[0]['summary_text']

    def default_document(self,original_document):
        """
        Returns the default document.
        """
        document = original_document
        if len(self.tokenizer.encode(document)) > self.max_position_embeddings:
                document = self.tokenizer.decode(self.tokenizer.encode(document)[:self.max_position_embeddings - 1])  # -1 to account for [SEP] token
        return document

    def generate_summaries(self, dataset, prompt_template="summarize: {document}",
                           gen_summarizer=default_summarizer,
                           gen_document=default_document,
                           gen_prompt=default_prompt):
        """
        Generates summaries for a given dataset using a custom or default prompt.

        Args:
            dataset (Dataset): The dataset containing documents to summarize.
            prompt_template (str, optional): A template for the prompt, with placeholders
                                              like '{document}' for the text to summarize.
                                              If None, a default prompt is used.

        Returns:
            list: A list of generated summaries.
        """
        summary_count = 0;
        generated_summaries = []
        for example in dataset:
            document = example['document']
            # Generate the document in the format that the model needs
            document = gen_document(self,document)
            # Format the prompt with the document text
            prompt = gen_prompt(self,prompt_template=prompt_template,document=document)
            # Generate the summary using the model
            summary = gen_summarizer(self, prompt)
            generated_summaries.append(summary)
            print("Summarized document ", str(summary_count))
            summary_count += 1
            print(summary)

        return generated_summaries

()